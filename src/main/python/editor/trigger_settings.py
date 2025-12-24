# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtWidgets import (QHBoxLayout, QLabel, QVBoxLayout, QMessageBox, QWidget,
                              QSlider, QCheckBox, QPushButton, QComboBox, QFrame,
                              QSizePolicy, QScrollArea, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal

from editor.basic_editor import BasicEditor
from widgets.keyboard_widget import KeyboardWidget2
from widgets.square_button import SquareButton
from util import tr
from vial_device import VialKeyboard


class ClickableWidget(QWidget):
    """Widget that emits clicked signal when clicked anywhere"""
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class TriggerSettingsTab(BasicEditor):
    """Per-key actuation settings editor"""

    def __init__(self, layout_editor):
        print("TriggerSettingsTab.__init__ called")
        super().__init__()

        self.layout_editor = layout_editor
        self.keyboard = None
        self.current_layer = 0
        self.syncing = False
        self.actuation_widget_ref = None  # Reference to QuickActuationWidget for synchronization

        # Cache for per-key actuation values (70 keys × 12 layers)
        self.per_key_values = []
        for layer in range(12):
            self.per_key_values.append([60] * 70)  # Default: 60 = 1.5mm

        # Mode flags
        self.mode_enabled = False
        self.per_layer_enabled = False

        # Cache for layer actuation settings (from Actuation Settings tab)
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

        # Top bar with layer selection
        self.layout_layers = QHBoxLayout()
        self.layout_size = QVBoxLayout()
        layer_label = QLabel(tr("TriggerSettings", "Layer"))

        layout_labels_container = QHBoxLayout()
        layout_labels_container.addWidget(layer_label)
        layout_labels_container.addLayout(self.layout_layers)
        layout_labels_container.addStretch()
        layout_labels_container.addLayout(self.layout_size)

        # Keyboard display
        self.container = KeyboardWidget2(layout_editor)
        self.container.clicked.connect(self.on_key_clicked)
        self.container.deselected.connect(self.on_key_deselected)

        # Keyboard area with layer buttons
        keyboard_area = QVBoxLayout()
        keyboard_area.addLayout(layout_labels_container)

        keyboard_layout = QHBoxLayout()
        keyboard_layout.addStretch(1)
        keyboard_layout.addWidget(self.container, 0, Qt.AlignTop)
        keyboard_layout.addStretch(1)
        keyboard_area.addLayout(keyboard_layout)

        w = ClickableWidget()
        w.setLayout(keyboard_area)
        w.clicked.connect(self.on_empty_space_clicked)

        # Wrap keyboard area in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setWidget(w)

        # Control panel at bottom
        control_panel = self.create_control_panel()

        self.layer_buttons = []
        self.device = None

        layout_editor.changed.connect(self.on_layout_changed)

        # Add widgets to BasicEditor layout (QVBoxLayout)
        self.addWidget(scroll_area)
        self.addWidget(control_panel)

    def create_control_panel(self):
        """Create the bottom control panel with tabbed interface"""
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        panel.setMaximumHeight(400)  # Increased to accommodate tabs
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 10, 20, 10)

        # Top checkboxes row (outside tabs)
        checkbox_row = QHBoxLayout()

        self.enable_checkbox = QCheckBox(tr("TriggerSettings", "Enable Per-Key Actuation"))
        self.enable_checkbox.setStyleSheet("QCheckBox { font-weight: bold; }")
        self.enable_checkbox.stateChanged.connect(self.on_enable_changed)
        checkbox_row.addWidget(self.enable_checkbox)

        self.per_layer_checkbox = QCheckBox(tr("TriggerSettings", "Enable Per-Layer Actuation"))
        self.per_layer_checkbox.stateChanged.connect(self.on_per_layer_changed)
        checkbox_row.addWidget(self.per_layer_checkbox)

        checkbox_row.addStretch()
        layout.addLayout(checkbox_row)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create Basic tab
        self.basic_tab = self.create_basic_tab()
        self.tab_widget.addTab(self.basic_tab, "Basic")

        # Create Rapidfire tab
        self.rapidfire_tab = self.create_rapidfire_tab()
        self.tab_widget.addTab(self.rapidfire_tab, "Rapidfire")

        # Bottom buttons row (outside tabs)
        button_row = QHBoxLayout()

        self.copy_layer_btn = QPushButton(tr("TriggerSettings", "Copy from Layer..."))
        self.copy_layer_btn.setEnabled(False)
        self.copy_layer_btn.clicked.connect(self.on_copy_layer)
        button_row.addWidget(self.copy_layer_btn)

        self.copy_all_layers_btn = QPushButton(tr("TriggerSettings", "Copy Per-Key Settings to All Layers"))
        self.copy_all_layers_btn.setEnabled(False)
        self.copy_all_layers_btn.clicked.connect(self.on_copy_to_all_layers)
        button_row.addWidget(self.copy_all_layers_btn)

        self.reset_btn = QPushButton(tr("TriggerSettings", "Reset All to Default"))
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self.on_reset_all)
        button_row.addWidget(self.reset_btn)

        button_row.addStretch()
        layout.addLayout(button_row)

        panel.setLayout(layout)
        return panel

    def create_basic_tab(self):
        """Create the Basic settings tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create a horizontal layout for the three vertical sliders
        sliders_layout = QHBoxLayout()

        # Key Actuation slider (for selected key) - VERTICAL
        key_actuation_container = QVBoxLayout()
        key_actuation_label = QLabel(tr("TriggerSettings", "Key Actuation"))
        key_actuation_label.setAlignment(Qt.AlignCenter)
        key_actuation_container.addWidget(key_actuation_label)

        self.actuation_value_label = QLabel("1.5mm")
        self.actuation_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        self.actuation_value_label.setAlignment(Qt.AlignCenter)
        key_actuation_container.addWidget(self.actuation_value_label)

        self.actuation_slider = QSlider(Qt.Vertical)
        self.actuation_slider.setMinimum(0)
        self.actuation_slider.setMaximum(100)
        self.actuation_slider.setValue(60)
        self.actuation_slider.setEnabled(False)
        self.actuation_slider.valueChanged.connect(self.on_key_actuation_changed)
        self.actuation_slider.setMinimumHeight(150)
        key_actuation_container.addWidget(self.actuation_slider, 1, Qt.AlignCenter)

        # Wrap in widget for hiding
        self.key_actuation_widget = QWidget()
        self.key_actuation_widget.setLayout(key_actuation_container)
        self.key_actuation_widget.setVisible(False)  # Hidden by default
        sliders_layout.addWidget(self.key_actuation_widget)

        # Normal Keys slider - VERTICAL
        normal_container = QVBoxLayout()
        normal_label = QLabel(tr("TriggerSettings", "Normal Keys"))
        normal_label.setAlignment(Qt.AlignCenter)
        normal_container.addWidget(normal_label)

        self.normal_value_label = QLabel("2.0mm")
        self.normal_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        self.normal_value_label.setAlignment(Qt.AlignCenter)
        normal_container.addWidget(self.normal_value_label)

        self.normal_slider = QSlider(Qt.Vertical)
        self.normal_slider.setMinimum(0)
        self.normal_slider.setMaximum(100)
        self.normal_slider.setValue(80)
        self.normal_slider.valueChanged.connect(self.on_normal_changed)
        self.normal_slider.setMinimumHeight(150)
        normal_container.addWidget(self.normal_slider, 1, Qt.AlignCenter)

        # Wrap in widget for hiding
        self.normal_widget = QWidget()
        self.normal_widget.setLayout(normal_container)
        sliders_layout.addWidget(self.normal_widget)

        # MIDI Keys slider - VERTICAL
        midi_container = QVBoxLayout()
        midi_label = QLabel(tr("TriggerSettings", "MIDI Keys"))
        midi_label.setAlignment(Qt.AlignCenter)
        midi_container.addWidget(midi_label)

        self.midi_value_label = QLabel("2.0mm")
        self.midi_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        self.midi_value_label.setAlignment(Qt.AlignCenter)
        midi_container.addWidget(self.midi_value_label)

        self.midi_slider = QSlider(Qt.Vertical)
        self.midi_slider.setMinimum(0)
        self.midi_slider.setMaximum(100)
        self.midi_slider.setValue(80)
        self.midi_slider.valueChanged.connect(self.on_midi_changed)
        self.midi_slider.setMinimumHeight(150)
        midi_container.addWidget(self.midi_slider, 1, Qt.AlignCenter)

        # Wrap in widget for hiding
        self.midi_widget = QWidget()
        self.midi_widget.setLayout(midi_container)
        sliders_layout.addWidget(self.midi_widget)

        layout.addLayout(sliders_layout)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Velocity Mode combo
        velocity_layout = QHBoxLayout()
        velocity_label = QLabel(tr("TriggerSettings", "Velocity Mode:"))
        velocity_label.setMinimumWidth(100)
        velocity_layout.addWidget(velocity_label)

        self.velocity_combo = QComboBox()
        self.velocity_combo.addItem("Fixed (64)", 0)
        self.velocity_combo.addItem("Peak at Apex", 1)
        self.velocity_combo.addItem("Speed-Based", 2)
        self.velocity_combo.addItem("Speed + Peak", 3)
        self.velocity_combo.setCurrentIndex(2)
        self.velocity_combo.currentIndexChanged.connect(self.on_velocity_mode_changed)
        velocity_layout.addWidget(self.velocity_combo, 1)

        layout.addLayout(velocity_layout)

        # Velocity Speed Scale slider
        vel_speed_layout = QHBoxLayout()
        vel_speed_label = QLabel(tr("TriggerSettings", "Velocity Scale:"))
        vel_speed_label.setMinimumWidth(100)
        vel_speed_layout.addWidget(vel_speed_label)

        self.vel_speed_slider = QSlider(Qt.Horizontal)
        self.vel_speed_slider.setMinimum(1)
        self.vel_speed_slider.setMaximum(20)
        self.vel_speed_slider.setValue(10)
        self.vel_speed_slider.valueChanged.connect(self.on_vel_speed_changed)
        vel_speed_layout.addWidget(self.vel_speed_slider, 1)

        self.vel_speed_value_label = QLabel("10")
        self.vel_speed_value_label.setMinimumWidth(60)
        self.vel_speed_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        vel_speed_layout.addWidget(self.vel_speed_value_label)

        layout.addLayout(vel_speed_layout)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def create_rapidfire_tab(self):
        """Create the Rapidfire settings tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Enable Rapidfire checkbox
        self.rapid_checkbox = QCheckBox(tr("TriggerSettings", "Enable Rapidfire"))
        self.rapid_checkbox.stateChanged.connect(self.on_rapidfire_toggled)
        layout.addWidget(self.rapid_checkbox)

        # Rapidfire Sensitivity slider
        rapid_layout = QHBoxLayout()
        rapid_label = QLabel(tr("TriggerSettings", "RF Sensitivity:"))
        rapid_label.setMinimumWidth(100)
        rapid_layout.addWidget(rapid_label)

        self.rapid_slider = QSlider(Qt.Horizontal)
        self.rapid_slider.setMinimum(1)
        self.rapid_slider.setMaximum(100)
        self.rapid_slider.setValue(4)
        self.rapid_slider.setEnabled(False)
        self.rapid_slider.valueChanged.connect(self.on_rapid_changed)
        rapid_layout.addWidget(self.rapid_slider, 1)

        self.rapid_value_label = QLabel("4")
        self.rapid_value_label.setMinimumWidth(60)
        self.rapid_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        rapid_layout.addWidget(self.rapid_value_label)

        layout.addLayout(rapid_layout)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Enable MIDI Rapidfire checkbox
        self.midi_rapid_checkbox = QCheckBox(tr("TriggerSettings", "Enable MIDI Rapidfire"))
        self.midi_rapid_checkbox.stateChanged.connect(self.on_midi_rapidfire_toggled)
        layout.addWidget(self.midi_rapid_checkbox)

        # MIDI Rapidfire Sensitivity slider
        midi_rapid_sens_layout = QHBoxLayout()
        midi_rapid_sens_label = QLabel(tr("TriggerSettings", "MRF Sens:"))
        midi_rapid_sens_label.setMinimumWidth(100)
        midi_rapid_sens_layout.addWidget(midi_rapid_sens_label)

        self.midi_rapid_sens_slider = QSlider(Qt.Horizontal)
        self.midi_rapid_sens_slider.setMinimum(1)
        self.midi_rapid_sens_slider.setMaximum(100)
        self.midi_rapid_sens_slider.setValue(10)
        self.midi_rapid_sens_slider.setEnabled(False)
        self.midi_rapid_sens_slider.valueChanged.connect(self.on_midi_rapid_sens_changed)
        midi_rapid_sens_layout.addWidget(self.midi_rapid_sens_slider, 1)

        self.midi_rapid_sens_value_label = QLabel("10")
        self.midi_rapid_sens_value_label.setMinimumWidth(60)
        self.midi_rapid_sens_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_rapid_sens_layout.addWidget(self.midi_rapid_sens_value_label)

        layout.addLayout(midi_rapid_sens_layout)

        # MIDI Rapidfire Velocity Range slider
        midi_rapid_vel_layout = QHBoxLayout()
        midi_rapid_vel_label = QLabel(tr("TriggerSettings", "MRF Vel Range:"))
        midi_rapid_vel_label.setMinimumWidth(100)
        midi_rapid_vel_layout.addWidget(midi_rapid_vel_label)

        self.midi_rapid_vel_slider = QSlider(Qt.Horizontal)
        self.midi_rapid_vel_slider.setMinimum(0)
        self.midi_rapid_vel_slider.setMaximum(20)
        self.midi_rapid_vel_slider.setValue(10)
        self.midi_rapid_vel_slider.setEnabled(False)
        self.midi_rapid_vel_slider.valueChanged.connect(self.on_midi_rapid_vel_changed)
        midi_rapid_vel_layout.addWidget(self.midi_rapid_vel_slider, 1)

        self.midi_rapid_vel_value_label = QLabel("±10")
        self.midi_rapid_vel_value_label.setMinimumWidth(60)
        self.midi_rapid_vel_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_rapid_vel_layout.addWidget(self.midi_rapid_vel_value_label)

        layout.addLayout(midi_rapid_vel_layout)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def value_to_mm(self, value):
        """Convert 0-100 value to millimeters string"""
        mm = (value / 40.0)  # 0-100 maps to 0-2.5mm (100/40 = 2.5)
        return f"{mm:.1f}mm"

    def on_empty_space_clicked(self):
        """Deselect key when clicking empty space"""
        self.container.deselect()
        self.container.update()

    def on_key_clicked(self):
        """Handle key click - load its actuation value"""
        if self.container.active_key is None:
            return

        key = self.container.active_key
        if key.desc.row is None:
            # Encoder, not a key
            return

        row, col = key.desc.row, key.desc.col
        key_index = row * 14 + col

        if key_index >= 70:
            return

        # Get current layer to use
        layer = self.current_layer if self.per_layer_enabled else 0

        # Load value to slider
        value = self.per_key_values[layer][key_index]
        self.syncing = True
        self.actuation_slider.setValue(value)
        self.actuation_value_label.setText(self.value_to_mm(value))
        self.syncing = False

        # Enable slider when key is selected
        self.actuation_slider.setEnabled(self.mode_enabled and self.container.active_key is not None)

    def on_key_deselected(self):
        """Handle key deselection"""
        self.actuation_slider.setEnabled(False)

    def on_key_actuation_changed(self, value):
        """Handle key actuation slider value change (per-key mode)"""
        self.actuation_value_label.setText(self.value_to_mm(value))

        if self.syncing or not self.mode_enabled:
            return

        # Save to cache
        if self.container.active_key and self.container.active_key.desc.row is not None:
            row = self.container.active_key.desc.row
            col = self.container.active_key.desc.col
            key_index = row * 14 + col

            if key_index < 70:
                layer = self.current_layer if self.per_layer_enabled else 0
                self.per_key_values[layer][key_index] = value

                # Send to device
                if self.device and isinstance(self.device, VialKeyboard):
                    self.device.keyboard.set_per_key_actuation(layer, row, col, value)

                # Refresh display
                self.refresh_layer_display()

    def on_normal_changed(self, value):
        """Handle normal keys actuation slider change"""
        self.normal_value_label.setText(self.value_to_mm(value))

        if self.syncing:
            return

        if self.per_layer_enabled:
            # Save to current layer only
            self.layer_data[self.current_layer]['normal'] = value
            if self.device and isinstance(self.device, VialKeyboard):
                self.send_layer_actuation(self.current_layer)
        else:
            # Save to ALL layers
            for layer in range(12):
                self.layer_data[layer]['normal'] = value
                if self.device and isinstance(self.device, VialKeyboard):
                    self.send_layer_actuation(layer)

    def on_midi_changed(self, value):
        """Handle MIDI keys actuation slider change"""
        self.midi_value_label.setText(self.value_to_mm(value))

        if self.syncing:
            return

        if self.per_layer_enabled:
            # Save to current layer only
            self.layer_data[self.current_layer]['midi'] = value
            if self.device and isinstance(self.device, VialKeyboard):
                self.send_layer_actuation(self.current_layer)
        else:
            # Save to ALL layers
            for layer in range(12):
                self.layer_data[layer]['midi'] = value
                if self.device and isinstance(self.device, VialKeyboard):
                    self.send_layer_actuation(layer)

    def on_velocity_mode_changed(self, index):
        """Handle velocity mode combo change"""
        if self.syncing:
            return

        velocity_value = self.velocity_combo.currentData()

        if self.per_layer_enabled:
            # Save to current layer only
            self.layer_data[self.current_layer]['velocity'] = velocity_value
            if self.device and isinstance(self.device, VialKeyboard):
                self.send_layer_actuation(self.current_layer)
        else:
            # Save to ALL layers
            for layer in range(12):
                self.layer_data[layer]['velocity'] = velocity_value
                if self.device and isinstance(self.device, VialKeyboard):
                    self.send_layer_actuation(layer)

    def on_vel_speed_changed(self, value):
        """Handle velocity speed scale slider change"""
        self.vel_speed_value_label.setText(str(value))

        if self.syncing:
            return

        if self.per_layer_enabled:
            # Save to current layer only
            self.layer_data[self.current_layer]['vel_speed'] = value
            if self.device and isinstance(self.device, VialKeyboard):
                self.send_layer_actuation(self.current_layer)
        else:
            # Save to ALL layers
            for layer in range(12):
                self.layer_data[layer]['vel_speed'] = value
                if self.device and isinstance(self.device, VialKeyboard):
                    self.send_layer_actuation(layer)

    def on_rapidfire_toggled(self, state):
        """Handle rapidfire checkbox toggle"""
        enabled = (state == Qt.Checked)
        self.rapid_slider.setEnabled(enabled)

        if self.syncing:
            return

        if self.per_layer_enabled:
            # Save to current layer only
            self.layer_data[self.current_layer]['rapidfire_enabled'] = enabled
            if self.device and isinstance(self.device, VialKeyboard):
                self.send_layer_actuation(self.current_layer)
        else:
            # Save to ALL layers
            for layer in range(12):
                self.layer_data[layer]['rapidfire_enabled'] = enabled
                if self.device and isinstance(self.device, VialKeyboard):
                    self.send_layer_actuation(layer)

    def on_rapid_changed(self, value):
        """Handle rapidfire sensitivity slider change"""
        self.rapid_value_label.setText(str(value))

        if self.syncing:
            return

        if self.per_layer_enabled:
            # Save to current layer only
            self.layer_data[self.current_layer]['rapid'] = value
            if self.device and isinstance(self.device, VialKeyboard):
                self.send_layer_actuation(self.current_layer)
        else:
            # Save to ALL layers
            for layer in range(12):
                self.layer_data[layer]['rapid'] = value
                if self.device and isinstance(self.device, VialKeyboard):
                    self.send_layer_actuation(layer)

    def on_midi_rapidfire_toggled(self, state):
        """Handle MIDI rapidfire checkbox toggle"""
        enabled = (state == Qt.Checked)
        self.midi_rapid_sens_slider.setEnabled(enabled)
        self.midi_rapid_vel_slider.setEnabled(enabled)

        if self.syncing:
            return

        if self.per_layer_enabled:
            # Save to current layer only
            self.layer_data[self.current_layer]['midi_rapidfire_enabled'] = enabled
            if self.device and isinstance(self.device, VialKeyboard):
                self.send_layer_actuation(self.current_layer)
        else:
            # Save to ALL layers
            for layer in range(12):
                self.layer_data[layer]['midi_rapidfire_enabled'] = enabled
                if self.device and isinstance(self.device, VialKeyboard):
                    self.send_layer_actuation(layer)

    def on_midi_rapid_sens_changed(self, value):
        """Handle MIDI rapidfire sensitivity slider change"""
        self.midi_rapid_sens_value_label.setText(str(value))

        if self.syncing:
            return

        if self.per_layer_enabled:
            # Save to current layer only
            self.layer_data[self.current_layer]['midi_rapid_sens'] = value
            if self.device and isinstance(self.device, VialKeyboard):
                self.send_layer_actuation(self.current_layer)
        else:
            # Save to ALL layers
            for layer in range(12):
                self.layer_data[layer]['midi_rapid_sens'] = value
                if self.device and isinstance(self.device, VialKeyboard):
                    self.send_layer_actuation(layer)

    def on_midi_rapid_vel_changed(self, value):
        """Handle MIDI rapidfire velocity range slider change"""
        self.midi_rapid_vel_value_label.setText(f"±{value}")

        if self.syncing:
            return

        if self.per_layer_enabled:
            # Save to current layer only
            self.layer_data[self.current_layer]['midi_rapid_vel'] = value
            if self.device and isinstance(self.device, VialKeyboard):
                self.send_layer_actuation(self.current_layer)
        else:
            # Save to ALL layers
            for layer in range(12):
                self.layer_data[layer]['midi_rapid_vel'] = value
                if self.device and isinstance(self.device, VialKeyboard):
                    self.send_layer_actuation(layer)

    def send_layer_actuation(self, layer):
        """Send layer actuation settings to device"""
        data = self.layer_data[layer]

        # Build flags byte
        flags = 0
        if data['rapidfire_enabled']:
            flags |= 0x01  # Bit 0
        if data['midi_rapidfire_enabled']:
            flags |= 0x02  # Bit 1

        # Build payload: [layer, normal, midi, velocity, rapid, midi_rapid_sens, midi_rapid_vel, vel_speed, flags]
        payload = bytes([
            layer,
            data['normal'],
            data['midi'],
            data['velocity'],
            data['rapid'],
            data['midi_rapid_sens'],
            data['midi_rapid_vel'],
            data['vel_speed'],
            flags
        ])

        # Send to device
        self.device.keyboard.set_layer_actuation(payload)

    def on_enable_changed(self, state):
        """Handle enable checkbox toggle"""
        if self.syncing:
            return

        self.mode_enabled = (state == Qt.Checked)
        # Keep per_layer_checkbox always enabled (arrays are not mutually exclusive)
        self.copy_layer_btn.setEnabled(self.mode_enabled)
        self.copy_all_layers_btn.setEnabled(self.mode_enabled)
        self.reset_btn.setEnabled(self.mode_enabled)

        # Implement visibility logic
        self.update_slider_states()

        # Update device
        if self.device and isinstance(self.device, VialKeyboard):
            self.device.keyboard.set_per_key_mode(self.mode_enabled, self.per_layer_enabled)

        self.refresh_layer_display()

    def update_slider_states(self):
        """Update slider visibility based on per-key mode"""
        if self.mode_enabled:
            # Per-key enabled: HIDE Normal/MIDI sliders, SHOW Key Actuation
            self.normal_widget.setVisible(False)
            self.midi_widget.setVisible(False)
            self.key_actuation_widget.setVisible(True)
        else:
            # Per-key disabled: SHOW Normal/MIDI sliders, HIDE Key Actuation
            self.normal_widget.setVisible(True)
            self.midi_widget.setVisible(True)
            self.key_actuation_widget.setVisible(False)

    def on_per_layer_changed(self, state):
        """Handle per-layer checkbox toggle"""
        if self.syncing:
            return

        self.per_layer_enabled = (state == Qt.Checked)

        # Update device
        if self.device and isinstance(self.device, VialKeyboard):
            self.device.keyboard.set_per_key_mode(self.mode_enabled, self.per_layer_enabled)

        # Synchronize with Actuation Settings tab
        if self.actuation_widget_ref:
            self.actuation_widget_ref.syncing = True
            self.actuation_widget_ref.per_layer_checkbox.setChecked(self.per_layer_enabled)
            self.actuation_widget_ref.syncing = False

        self.refresh_layer_display()

    def on_copy_layer(self):
        """Show dialog to copy actuations from another layer"""
        if not self.mode_enabled:
            return

        # Create simple combo box dialog
        msg = QMessageBox(self.widget())
        msg.setWindowTitle(tr("TriggerSettings", "Copy Layer"))
        msg.setText(tr("TriggerSettings", "Copy actuation settings from which layer?"))

        combo = QComboBox()
        for i in range(12):
            combo.addItem(f"Layer {i}", i)
        combo.setCurrentIndex(0 if self.current_layer == 0 else 0)

        msg.layout().addWidget(combo, 1, 1)
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

        if msg.exec_() == QMessageBox.Ok:
            source_layer = combo.currentData()
            dest_layer = self.current_layer

            # Copy in memory
            self.per_key_values[dest_layer] = self.per_key_values[source_layer].copy()

            # Copy on device
            if self.device and isinstance(self.device, VialKeyboard):
                self.device.keyboard.copy_layer_actuations(source_layer, dest_layer)

            self.refresh_layer_display()

    def on_copy_to_all_layers(self):
        """Copy current layer's per-key settings to all layers"""
        if not self.mode_enabled:
            return

        ret = QMessageBox.question(
            self.widget(),
            tr("TriggerSettings", "Copy to All Layers"),
            tr("TriggerSettings", f"Copy per-key settings from Layer {self.current_layer} to all layers?"),
            QMessageBox.Yes | QMessageBox.No
        )

        if ret == QMessageBox.Yes:
            source_layer = self.current_layer

            # Copy to all layers in memory and on device
            for dest_layer in range(12):
                if dest_layer != source_layer:
                    # Copy in memory
                    self.per_key_values[dest_layer] = self.per_key_values[source_layer].copy()

                    # Copy on device
                    if self.device and isinstance(self.device, VialKeyboard):
                        self.device.keyboard.copy_layer_actuations(source_layer, dest_layer)

            self.refresh_layer_display()
            QMessageBox.information(
                self.widget(),
                tr("TriggerSettings", "Copy Complete"),
                tr("TriggerSettings", f"Per-key settings copied to all layers.")
            )

    def on_reset_all(self):
        """Reset all actuations to default with confirmation"""
        ret = QMessageBox.question(
            self.widget(),
            tr("TriggerSettings", "Reset All"),
            tr("TriggerSettings", "Reset all per-key actuations to default (1.5mm)?"),
            QMessageBox.Yes | QMessageBox.No
        )

        if ret == QMessageBox.Yes:
            # Reset in memory
            for layer in range(12):
                self.per_key_values[layer] = [60] * 70

            # Reset on device
            if self.device and isinstance(self.device, VialKeyboard):
                self.device.keyboard.reset_per_key_actuations()

            self.refresh_layer_display()

    def rebuild_layers(self):
        """Create layer selection buttons"""
        # Delete old buttons
        for btn in self.layer_buttons:
            btn.hide()
            btn.deleteLater()
        self.layer_buttons = []

        # Create layer buttons
        for x in range(self.keyboard.layers):
            btn = SquareButton(str(x))
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setRelSize(1.667)
            btn.setCheckable(True)
            btn.clicked.connect(lambda state, idx=x: self.switch_layer(idx))
            self.layout_layers.addWidget(btn)
            self.layer_buttons.append(btn)

        # Size adjustment buttons
        for x in range(0, 2):
            btn = SquareButton("-") if x else SquareButton("+")
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setCheckable(False)
            btn.clicked.connect(lambda state, idx=x: self.adjust_size(idx))
            self.layout_size.addWidget(btn)
            self.layer_buttons.append(btn)

    def adjust_size(self, minus):
        """Adjust keyboard display size"""
        if minus:
            self.container.set_scale(self.container.get_scale() - 0.1)
        else:
            self.container.set_scale(self.container.get_scale() + 0.1)
        self.refresh_layer_display()

    def switch_layer(self, layer):
        """Switch to a different layer"""
        self.current_layer = layer
        for idx, btn in enumerate(self.layer_buttons[:self.keyboard.layers]):
            btn.setChecked(idx == layer)

        # Load layer data into controls
        self.load_layer_controls()

        self.refresh_layer_display()

    def load_layer_controls(self):
        """Load current layer's data into control widgets"""
        if not self.valid():
            return

        layer = self.current_layer
        data = self.layer_data[layer]

        self.syncing = True

        # Load Basic tab controls
        self.normal_slider.setValue(data['normal'])
        self.normal_value_label.setText(self.value_to_mm(data['normal']))

        self.midi_slider.setValue(data['midi'])
        self.midi_value_label.setText(self.value_to_mm(data['midi']))

        # Set velocity combo by finding matching data value
        for i in range(self.velocity_combo.count()):
            if self.velocity_combo.itemData(i) == data['velocity']:
                self.velocity_combo.setCurrentIndex(i)
                break

        self.vel_speed_slider.setValue(data['vel_speed'])
        self.vel_speed_value_label.setText(str(data['vel_speed']))

        # Load Rapidfire tab controls
        self.rapid_checkbox.setChecked(data['rapidfire_enabled'])
        self.rapid_slider.setEnabled(data['rapidfire_enabled'])
        self.rapid_slider.setValue(data['rapid'])
        self.rapid_value_label.setText(str(data['rapid']))

        self.midi_rapid_checkbox.setChecked(data['midi_rapidfire_enabled'])
        self.midi_rapid_sens_slider.setEnabled(data['midi_rapidfire_enabled'])
        self.midi_rapid_vel_slider.setEnabled(data['midi_rapidfire_enabled'])
        self.midi_rapid_sens_slider.setValue(data['midi_rapid_sens'])
        self.midi_rapid_sens_value_label.setText(str(data['midi_rapid_sens']))
        self.midi_rapid_vel_slider.setValue(data['midi_rapid_vel'])
        self.midi_rapid_vel_value_label.setText(f"±{data['midi_rapid_vel']}")

        self.syncing = False

    def on_layout_changed(self):
        """Handle layout change from layout editor"""
        self.refresh_layer_display()

    def rebuild(self, device):
        """Rebuild UI with new device"""
        print(f"TriggerSettingsTab.rebuild() called with device={device}")
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard

            self.rebuild_layers()
            self.container.set_keys(self.keyboard.keys, self.keyboard.encoders)
            self.current_layer = 0

            # Load mode flags from device
            mode_data = self.keyboard.get_per_key_mode()
            if mode_data:
                self.syncing = True
                self.mode_enabled = mode_data['mode_enabled']
                self.per_layer_enabled = mode_data['per_layer_enabled']
                self.enable_checkbox.setChecked(self.mode_enabled)
                self.per_layer_checkbox.setChecked(self.per_layer_enabled)
                # Keep per_layer_checkbox always enabled
                self.copy_layer_btn.setEnabled(self.mode_enabled)
                self.copy_all_layers_btn.setEnabled(self.mode_enabled)
                self.reset_btn.setEnabled(self.mode_enabled)
                self.syncing = False

            # Load all per-key values from device
            for layer in range(12):
                for row in range(5):
                    for col in range(14):
                        key_index = row * 14 + col
                        if key_index < 70:
                            value = self.keyboard.get_per_key_actuation(layer, row, col)
                            if value is not None:
                                self.per_key_values[layer][key_index] = value

            # Load layer actuation data from device
            try:
                actuations = self.keyboard.get_all_layer_actuations()
                if actuations and len(actuations) == 96:  # 12 layers × 8 bytes
                    for layer in range(12):
                        offset = layer * 8
                        flags = actuations[offset + 7]

                        self.layer_data[layer] = {
                            'normal': actuations[offset + 0],
                            'midi': actuations[offset + 1],
                            'velocity': actuations[offset + 2],
                            'rapid': actuations[offset + 3],
                            'midi_rapid_sens': actuations[offset + 4],
                            'midi_rapid_vel': actuations[offset + 5],
                            'vel_speed': actuations[offset + 6],
                            'rapidfire_enabled': bool(flags & 0x01),
                            'midi_rapidfire_enabled': bool(flags & 0x02)
                        }
            except Exception as e:
                print(f"Error loading layer actuations: {e}")

            # Update slider states
            self.update_slider_states()

            # Load current layer data into controls
            self.load_layer_controls()

            self.refresh_layer_display()

        self.container.setEnabled(self.valid())

    def valid(self):
        """Check if device is valid"""
        result = isinstance(self.device, VialKeyboard)
        print(f"TriggerSettingsTab.valid() called: device={self.device}, result={result}")
        return result

    def refresh_layer_display(self):
        """Refresh keyboard display with actuation values"""
        if not self.valid():
            return

        # Update layer button highlighting
        for idx, btn in enumerate(self.layer_buttons[:self.keyboard.layers]):
            btn.setChecked(idx == self.current_layer)

        # Update keyboard key displays
        layer = self.current_layer if self.per_layer_enabled else 0

        for key in self.container.widgets:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    value = self.per_key_values[layer][key_index]
                    # Display as "X.Xmm" on the key
                    key.setText(self.value_to_mm(value))
                else:
                    key.setText("")

        self.container.update()

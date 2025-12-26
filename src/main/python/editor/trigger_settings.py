# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtWidgets import (QHBoxLayout, QLabel, QVBoxLayout, QMessageBox, QWidget,
                              QSlider, QCheckBox, QPushButton, QComboBox, QFrame,
                              QSizePolicy, QScrollArea, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal

from editor.basic_editor import BasicEditor
from widgets.keyboard_widget import KeyboardWidget2
from widgets.square_button import SquareButton
from widgets.range_slider import TriggerSlider, RapidTriggerSlider
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
        # Each key now stores 8 fields
        # Note: deadzone values are ALWAYS enabled (non-zero by default)
        self.per_key_values = []
        for layer in range(12):
            layer_keys = []
            for _ in range(70):
                layer_keys.append({
                    'actuation': 60,                    # 0-100 = 0-2.5mm, default 1.5mm (60/40 = 1.5)
                    'deadzone_top': 4,                  # 0-20 = 0-0.5mm, default 0.1mm (4/40 = 0.1) - FROM RIGHT
                    'deadzone_bottom': 4,               # 0-20 = 0-0.5mm, default 0.1mm (4/40 = 0.1) - FROM LEFT
                    'velocity_curve': 2,                # 0-4 (SOFTEST, SOFT, MEDIUM, HARD, HARDEST), default MEDIUM
                    'flags': 0,                         # Bit 0: rapidfire_enabled, Bit 1: use_per_key_velocity_curve
                    'rapidfire_press_sens': 4,          # 1-100 = 0.025-2.5mm, default 0.1mm (4/40 = 0.1) - FROM LEFT
                    'rapidfire_release_sens': 4,        # 1-100 = 0.025-2.5mm, default 0.1mm (4/40 = 0.1) - FROM RIGHT
                    'rapidfire_velocity_mod': 0         # -64 to +64, default 0
                })
            self.per_key_values.append(layer_keys)

        # Mode flags
        self.mode_enabled = False
        self.per_layer_enabled = False

        # Cache for layer actuation settings
        self.layer_data = []
        for _ in range(12):
            self.layer_data.append({
                'normal': 80,
                'midi': 80,
                'velocity': 2,  # Velocity mode (0=Fixed, 1=Peak, 2=Speed, 3=Speed+Peak)
                'vel_speed': 10  # Velocity speed scale
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

        # Selection buttons column (left of keyboard)
        selection_buttons_layout = QVBoxLayout()

        self.select_all_btn = QPushButton(tr("TriggerSettings", "Select All"))
        self.select_all_btn.clicked.connect(self.on_select_all)
        selection_buttons_layout.addWidget(self.select_all_btn)

        self.unselect_all_btn = QPushButton(tr("TriggerSettings", "Unselect All"))
        self.unselect_all_btn.clicked.connect(self.on_unselect_all)
        selection_buttons_layout.addWidget(self.unselect_all_btn)

        self.invert_selection_btn = QPushButton(tr("TriggerSettings", "Invert Selection"))
        self.invert_selection_btn.clicked.connect(self.on_invert_selection)
        selection_buttons_layout.addWidget(self.invert_selection_btn)

        selection_buttons_layout.addStretch()

        # Keyboard area with layer buttons
        keyboard_area = QVBoxLayout()
        keyboard_area.addLayout(layout_labels_container)

        keyboard_layout = QHBoxLayout()
        keyboard_layout.addLayout(selection_buttons_layout)
        keyboard_layout.addWidget(self.container, 0, Qt.AlignTop)
        keyboard_layout.addStretch(1)
        keyboard_area.addLayout(keyboard_layout)
        keyboard_area.setContentsMargins(0, 0, 0, 0)  # Remove bottom margin

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
        layout.setSpacing(5)
        layout.setContentsMargins(20, 5, 20, 10)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create Basic tab (without title since tab already has label)
        self.basic_tab = self.create_basic_tab()
        self.tab_widget.addTab(self.basic_tab, "Settings")

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
        """Create the Per-Key Settings tab"""
        tab = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 5, 10, 10)

        # Top checkboxes row
        checkbox_row = QHBoxLayout()

        self.enable_checkbox = QCheckBox(tr("TriggerSettings", "Enable Per-Key Actuation"))
        self.enable_checkbox.setStyleSheet("QCheckBox { font-weight: bold; }")
        self.enable_checkbox.stateChanged.connect(self.on_enable_changed)
        checkbox_row.addWidget(self.enable_checkbox)

        self.per_layer_checkbox = QCheckBox(tr("TriggerSettings", "Enable Per-Layer Actuation"))
        self.per_layer_checkbox.stateChanged.connect(self.on_per_layer_changed)
        checkbox_row.addWidget(self.per_layer_checkbox)

        checkbox_row.addStretch()
        main_layout.addLayout(checkbox_row)

        # Info label
        info_label = QLabel(tr("TriggerSettings", "Select a key to configure its settings"))
        info_label.setStyleSheet("QLabel { font-style: italic; color: gray; font-size: 9pt; }")
        main_layout.addWidget(info_label)

        # Scroll area for all controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # === ACTUATION SECTION ===
        # Container for actuation sliders that will swap based on mode

        # Global actuation sliders (shown when per-key mode is disabled)
        self.global_actuation_widget = QWidget()
        global_actuation_layout = QVBoxLayout()
        global_actuation_layout.setSpacing(8)
        global_actuation_layout.setContentsMargins(0, 0, 0, 0)

        # Normal Keys Actuation slider
        normal_layout = QHBoxLayout()
        normal_label = QLabel(tr("TriggerSettings", "Normal Keys:"))
        normal_label.setMinimumWidth(140)
        normal_layout.addWidget(normal_label)

        self.global_normal_slider = QSlider(Qt.Horizontal)
        self.global_normal_slider.setMinimum(0)
        self.global_normal_slider.setMaximum(100)
        self.global_normal_slider.setValue(80)
        self.global_normal_slider.valueChanged.connect(self.on_global_normal_changed)
        normal_layout.addWidget(self.global_normal_slider, 1)

        self.global_normal_value_label = QLabel("2.00mm")
        self.global_normal_value_label.setMinimumWidth(80)
        self.global_normal_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        normal_layout.addWidget(self.global_normal_value_label)

        global_actuation_layout.addLayout(normal_layout)

        # MIDI Keys Actuation slider
        midi_layout = QHBoxLayout()
        midi_label = QLabel(tr("TriggerSettings", "MIDI Keys:"))
        midi_label.setMinimumWidth(140)
        midi_layout.addWidget(midi_label)

        self.global_midi_slider = QSlider(Qt.Horizontal)
        self.global_midi_slider.setMinimum(0)
        self.global_midi_slider.setMaximum(100)
        self.global_midi_slider.setValue(80)
        self.global_midi_slider.valueChanged.connect(self.on_global_midi_changed)
        midi_layout.addWidget(self.global_midi_slider, 1)

        self.global_midi_value_label = QLabel("2.00mm")
        self.global_midi_value_label.setMinimumWidth(80)
        self.global_midi_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_layout.addWidget(self.global_midi_value_label)

        global_actuation_layout.addLayout(midi_layout)

        self.global_actuation_widget.setLayout(global_actuation_layout)
        self.global_actuation_widget.setVisible(True)  # Visible by default when mode_enabled is False
        layout.addWidget(self.global_actuation_widget)

        # Per-Key Actuation slider (shown when per-key mode is enabled)
        self.per_key_actuation_widget = QWidget()
        per_key_actuation_layout = QVBoxLayout()
        per_key_actuation_layout.setSpacing(12)
        per_key_actuation_layout.setContentsMargins(0, 0, 0, 0)

        # Title and value labels for the combined slider
        title_layout = QHBoxLayout()
        title_label = QLabel(tr("TriggerSettings", "Trigger Travel Configuration"))
        title_label.setStyleSheet("QLabel { font-weight: bold; font-size: 11pt; }")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        per_key_actuation_layout.addLayout(title_layout)

        # Value display row
        values_layout = QHBoxLayout()

        # Deadzone bottom label
        dz_bottom_container = QVBoxLayout()
        dz_bottom_title = QLabel("Deadzone Min")
        dz_bottom_title.setStyleSheet("QLabel { color: gray; font-size: 8pt; }")
        self.deadzone_bottom_value_label = QLabel("0.1mm")
        self.deadzone_bottom_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        dz_bottom_container.addWidget(dz_bottom_title)
        dz_bottom_container.addWidget(self.deadzone_bottom_value_label)
        values_layout.addLayout(dz_bottom_container)

        values_layout.addStretch()

        # Actuation label
        actuation_container = QVBoxLayout()
        actuation_title = QLabel("Actuation Point")
        actuation_title.setStyleSheet("QLabel { color: gray; font-size: 8pt; }")
        self.actuation_value_label = QLabel("1.5mm")
        self.actuation_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 12pt; color: #ff8c32; }")
        actuation_container.addWidget(actuation_title)
        actuation_container.addWidget(self.actuation_value_label)
        values_layout.addLayout(actuation_container)

        values_layout.addStretch()

        # Deadzone top label
        dz_top_container = QVBoxLayout()
        dz_top_title = QLabel("Deadzone Max")
        dz_top_title.setStyleSheet("QLabel { color: gray; font-size: 8pt; }")
        self.deadzone_top_value_label = QLabel("2.4mm")
        self.deadzone_top_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        dz_top_container.addWidget(dz_top_title)
        dz_top_container.addWidget(self.deadzone_top_value_label)
        values_layout.addLayout(dz_top_container)

        per_key_actuation_layout.addLayout(values_layout)

        # Combined trigger slider (deadzone bottom, actuation, deadzone top)
        self.trigger_slider = TriggerSlider(minimum=0, maximum=100)
        self.trigger_slider.setEnabled(False)
        self.trigger_slider.deadzoneBottomChanged.connect(self.on_deadzone_bottom_changed)
        self.trigger_slider.actuationChanged.connect(self.on_key_actuation_changed)
        self.trigger_slider.deadzoneTopChanged.connect(self.on_deadzone_top_changed)
        self.trigger_slider.setMinimumHeight(60)
        per_key_actuation_layout.addWidget(self.trigger_slider)

        self.per_key_actuation_widget.setLayout(per_key_actuation_layout)
        self.per_key_actuation_widget.setVisible(False)  # Hidden by default when mode_enabled is False
        layout.addWidget(self.per_key_actuation_widget)

        # Velocity Curve dropdown
        curve_layout = QHBoxLayout()
        curve_label = QLabel(tr("TriggerSettings", "Velocity Curve:"))
        curve_label.setMinimumWidth(140)
        curve_layout.addWidget(curve_label)

        self.velocity_curve_combo = QComboBox()
        self.velocity_curve_combo.addItem("Softest (x³)", 0)
        self.velocity_curve_combo.addItem("Soft (x²)", 1)
        self.velocity_curve_combo.addItem("Medium (x)", 2)
        self.velocity_curve_combo.addItem("Hard (√x)", 3)
        self.velocity_curve_combo.addItem("Hardest (∛x)", 4)
        self.velocity_curve_combo.setCurrentIndex(2)
        self.velocity_curve_combo.setEnabled(False)
        self.velocity_curve_combo.currentIndexChanged.connect(self.on_velocity_curve_changed)
        curve_layout.addWidget(self.velocity_curve_combo, 1)

        layout.addLayout(curve_layout)

        # Use Per-Key Velocity Curve checkbox
        self.use_per_key_curve_checkbox = QCheckBox(tr("TriggerSettings", "Use Per-Key Velocity Curve"))
        self.use_per_key_curve_checkbox.setToolTip("When enabled, this key uses its own velocity curve. When disabled, uses global velocity curve.")
        self.use_per_key_curve_checkbox.setEnabled(False)
        self.use_per_key_curve_checkbox.stateChanged.connect(self.on_use_per_key_curve_changed)
        layout.addWidget(self.use_per_key_curve_checkbox)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # === RAPIDFIRE SECTION ===
        # Enable Rapidfire checkbox
        self.rapidfire_checkbox = QCheckBox(tr("TriggerSettings", "Enable Rapidfire"))
        self.rapidfire_checkbox.setEnabled(False)
        self.rapidfire_checkbox.stateChanged.connect(self.on_rapidfire_toggled)
        layout.addWidget(self.rapidfire_checkbox)

        # Rapid Trigger combined slider widget
        self.rf_widget = QWidget()
        rf_layout = QVBoxLayout()
        rf_layout.setSpacing(12)
        rf_layout.setContentsMargins(0, 0, 0, 0)

        # Title and value labels
        rf_title_layout = QHBoxLayout()
        rf_title_label = QLabel(tr("TriggerSettings", "Rapid Trigger Sensitivity"))
        rf_title_label.setStyleSheet("QLabel { font-weight: bold; }")
        rf_title_layout.addWidget(rf_title_label)
        rf_title_layout.addStretch()
        rf_layout.addLayout(rf_title_layout)

        # Value display row
        rf_values_layout = QHBoxLayout()

        # Press sensitivity label
        press_container = QVBoxLayout()
        press_title = QLabel("Press Sensitivity")
        press_title.setStyleSheet("QLabel { color: gray; font-size: 8pt; }")
        self.rf_press_value_label = QLabel("0.1mm")
        self.rf_press_value_label.setStyleSheet("QLabel { font-weight: bold; color: #ff8c32; }")
        press_container.addWidget(press_title)
        press_container.addWidget(self.rf_press_value_label)
        rf_values_layout.addLayout(press_container)

        rf_values_layout.addStretch()

        # Release sensitivity label
        release_container = QVBoxLayout()
        release_title = QLabel("Release Sensitivity")
        release_title.setStyleSheet("QLabel { color: gray; font-size: 8pt; }")
        self.rf_release_value_label = QLabel("0.1mm")
        self.rf_release_value_label.setStyleSheet("QLabel { font-weight: bold; color: #64c8ff; }")
        release_container.addWidget(release_title)
        release_container.addWidget(self.rf_release_value_label)
        rf_values_layout.addLayout(release_container)

        rf_layout.addLayout(rf_values_layout)

        # Combined rapid trigger slider
        self.rapid_trigger_slider = RapidTriggerSlider(minimum=1, maximum=100)
        self.rapid_trigger_slider.setEnabled(False)
        self.rapid_trigger_slider.pressSensChanged.connect(self.on_rf_press_changed)
        self.rapid_trigger_slider.releaseSensChanged.connect(self.on_rf_release_changed)
        self.rapid_trigger_slider.setMinimumHeight(60)
        rf_layout.addWidget(self.rapid_trigger_slider)

        self.rf_widget.setLayout(rf_layout)
        self.rf_widget.setVisible(False)  # Hidden until rapidfire is enabled
        layout.addWidget(self.rf_widget)

        # Rapidfire Velocity Modifier slider
        rf_vel_mod_layout = QHBoxLayout()
        rf_vel_mod_label = QLabel(tr("TriggerSettings", "RF Velocity Mod:"))
        rf_vel_mod_label.setMinimumWidth(140)
        rf_vel_mod_layout.addWidget(rf_vel_mod_label)

        self.rf_vel_mod_slider = QSlider(Qt.Horizontal)
        self.rf_vel_mod_slider.setMinimum(-64)
        self.rf_vel_mod_slider.setMaximum(64)
        self.rf_vel_mod_slider.setValue(0)
        self.rf_vel_mod_slider.setEnabled(False)
        self.rf_vel_mod_slider.valueChanged.connect(self.on_rf_vel_mod_changed)
        rf_vel_mod_layout.addWidget(self.rf_vel_mod_slider, 1)

        self.rf_vel_mod_value_label = QLabel("0")
        self.rf_vel_mod_value_label.setMinimumWidth(80)
        self.rf_vel_mod_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        rf_vel_mod_layout.addWidget(self.rf_vel_mod_value_label)

        layout.addLayout(rf_vel_mod_layout)

        layout.addStretch()
        scroll_widget.setLayout(layout)
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        tab.setLayout(main_layout)
        return tab


    def value_to_mm(self, value):
        """Convert 0-100 value to millimeters string"""
        mm = (value / 40.0)  # 0-100 maps to 0-2.5mm (100/40 = 2.5)
        return f"{mm:.1f}mm"

    def on_global_normal_changed(self, value):
        """Handle global normal actuation slider change"""
        self.global_normal_value_label.setText(self.value_to_mm(value))

        if self.syncing:
            return

        # Update layer_data for current layer (or all layers if not per-layer)
        layer = self.current_layer if self.per_layer_enabled else 0

        if self.per_layer_enabled:
            # Update only current layer
            self.layer_data[layer]['normal'] = value
        else:
            # Update all layers
            for i in range(12):
                self.layer_data[i]['normal'] = value

        # Send to device
        if self.device and isinstance(self.device, VialKeyboard):
            self.send_layer_actuation(layer)

    def on_global_midi_changed(self, value):
        """Handle global MIDI actuation slider change"""
        self.global_midi_value_label.setText(self.value_to_mm(value))

        if self.syncing:
            return

        # Update layer_data for current layer (or all layers if not per-layer)
        layer = self.current_layer if self.per_layer_enabled else 0

        if self.per_layer_enabled:
            # Update only current layer
            self.layer_data[layer]['midi'] = value
        else:
            # Update all layers
            for i in range(12):
                self.layer_data[i]['midi'] = value

        # Send to device
        if self.device and isinstance(self.device, VialKeyboard):
            self.send_layer_actuation(layer)

    def on_empty_space_clicked(self):
        """Deselect key when clicking empty space"""
        self.container.deselect()
        self.container.update()

    def on_key_clicked(self):
        """Handle key click - load all per-key settings"""
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

        # Load all settings from cache
        settings = self.per_key_values[layer][key_index]
        self.syncing = True

        # Load trigger slider (actuation + deadzones)
        self.trigger_slider.set_deadzone_bottom(settings['deadzone_bottom'])
        self.trigger_slider.set_actuation(settings['actuation'])
        self.trigger_slider.set_deadzone_top(settings['deadzone_top'])

        # Update labels
        self.deadzone_bottom_value_label.setText(self.value_to_mm(settings['deadzone_bottom']))
        self.actuation_value_label.setText(self.value_to_mm(settings['actuation']))
        self.deadzone_top_value_label.setText(self.value_to_mm(settings['deadzone_top']))

        # Load velocity curve
        self.velocity_curve_combo.setCurrentIndex(settings['velocity_curve'])

        # Load rapidfire settings (extract bit 0 from flags)
        rapidfire_enabled = (settings['flags'] & 0x01) != 0
        self.rapidfire_checkbox.setChecked(rapidfire_enabled)

        # Load rapid trigger slider
        self.rapid_trigger_slider.set_press_sens(settings['rapidfire_press_sens'])
        self.rapid_trigger_slider.set_release_sens(settings['rapidfire_release_sens'])
        self.rf_press_value_label.setText(self.value_to_mm(settings['rapidfire_press_sens']))
        self.rf_release_value_label.setText(self.value_to_mm(settings['rapidfire_release_sens']))

        # Load velocity modifier
        self.rf_vel_mod_slider.setValue(settings['rapidfire_velocity_mod'])
        self.rf_vel_mod_value_label.setText(str(settings['rapidfire_velocity_mod']))

        # Load per-key velocity curve checkbox (extract bit 1 from flags)
        use_per_key_curve = (settings['flags'] & 0x02) != 0
        self.use_per_key_curve_checkbox.setChecked(use_per_key_curve)

        self.syncing = False

        # Enable controls when key is selected
        key_selected = self.container.active_key is not None
        self.trigger_slider.setEnabled(key_selected and self.mode_enabled)
        self.use_per_key_curve_checkbox.setEnabled(key_selected)
        self.velocity_curve_combo.setEnabled(key_selected and use_per_key_curve)
        self.rapidfire_checkbox.setEnabled(key_selected)
        self.rapid_trigger_slider.setEnabled(key_selected and rapidfire_enabled)
        self.rf_widget.setVisible(rapidfire_enabled)
        self.rf_vel_mod_slider.setEnabled(key_selected and rapidfire_enabled)

    def on_key_deselected(self):
        """Handle key deselection - disable all controls"""
        self.trigger_slider.setEnabled(False)
        self.velocity_curve_combo.setEnabled(False)
        self.rapidfire_checkbox.setEnabled(False)
        self.rapid_trigger_slider.setEnabled(False)
        self.rf_vel_mod_slider.setEnabled(False)
        self.rf_widget.setVisible(False)

    def save_current_key_settings(self):
        """Helper to save current key's settings to device"""
        if not self.container.active_key or self.container.active_key.desc.row is None:
            return

        row = self.container.active_key.desc.row
        col = self.container.active_key.desc.col
        key_index = row * 14 + col

        if key_index >= 70:
            return

        layer = self.current_layer if self.per_layer_enabled else 0
        settings = self.per_key_values[layer][key_index]

        # Send to device
        if self.device and isinstance(self.device, VialKeyboard):
            self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        # Refresh display
        self.refresh_layer_display()

    def on_key_actuation_changed(self, value):
        """Handle key actuation slider value change - applies to all selected keys"""
        self.actuation_value_label.setText(self.value_to_mm(value))

        if self.syncing or not self.mode_enabled:
            return

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    self.per_key_values[layer][key_index]['actuation'] = value
                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        self.refresh_layer_display()

    def on_velocity_curve_changed(self, index):
        """Handle velocity curve dropdown change - applies to all selected keys"""
        if self.syncing:
            return

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    self.per_key_values[layer][key_index]['velocity_curve'] = index
                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        self.refresh_layer_display()

    def on_deadzone_top_changed(self, value):
        """Handle top deadzone slider change - applies to all selected keys"""
        self.deadzone_top_value_label.setText(self.value_to_mm(value))

        if self.syncing:
            return

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    self.per_key_values[layer][key_index]['deadzone_top'] = value
                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        self.refresh_layer_display()

    def on_deadzone_bottom_changed(self, value):
        """Handle bottom deadzone slider change - applies to all selected keys"""
        self.deadzone_bottom_value_label.setText(self.value_to_mm(value))

        if self.syncing:
            return

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    self.per_key_values[layer][key_index]['deadzone_bottom'] = value
                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        self.refresh_layer_display()

    def on_rapidfire_toggled(self, state):
        """Handle rapidfire checkbox toggle"""
        enabled = (state == Qt.Checked)

        if not self.syncing:
            # Show/hide rapidfire widget and enable sliders
            self.rf_widget.setVisible(enabled)
            self.rapid_trigger_slider.setEnabled(enabled)
            self.rf_vel_mod_slider.setEnabled(enabled)

            # Get all selected keys (or just active key if none selected)
            selected_keys = self.container.get_selected_keys()
            if not selected_keys and self.container.active_key:
                selected_keys = [self.container.active_key]

            layer = self.current_layer if self.per_layer_enabled else 0

            # Apply to all selected keys
            for key in selected_keys:
                if key.desc.row is not None:
                    row, col = key.desc.row, key.desc.col
                    key_index = row * 14 + col

                    if key_index < 70:
                        # Update flags field: set or clear bit 0
                        if enabled:
                            self.per_key_values[layer][key_index]['flags'] |= 0x01  # Set bit 0
                        else:
                            self.per_key_values[layer][key_index]['flags'] &= ~0x01  # Clear bit 0

                        # Send to device
                        if self.device and isinstance(self.device, VialKeyboard):
                            settings = self.per_key_values[layer][key_index]
                            self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

            self.refresh_layer_display()

    def on_rf_press_changed(self, value):
        """Handle rapidfire press sensitivity slider change - applies to all selected keys"""
        self.rf_press_value_label.setText(self.value_to_mm(value))

        if self.syncing:
            return

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    self.per_key_values[layer][key_index]['rapidfire_press_sens'] = value
                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        self.refresh_layer_display()

    def on_rf_release_changed(self, value):
        """Handle rapidfire release sensitivity slider change - applies to all selected keys"""
        self.rf_release_value_label.setText(self.value_to_mm(value))

        if self.syncing:
            return

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    self.per_key_values[layer][key_index]['rapidfire_release_sens'] = value
                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        self.refresh_layer_display()

    def on_rf_vel_mod_changed(self, value):
        """Handle rapidfire velocity modifier slider change - applies to all selected keys"""
        self.rf_vel_mod_value_label.setText(str(value))

        if self.syncing:
            return

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    self.per_key_values[layer][key_index]['rapidfire_velocity_mod'] = value
                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        self.refresh_layer_display()

    def on_use_per_key_curve_changed(self, state):
        """Handle 'Use Per-Key Velocity Curve' checkbox toggle (per-key setting)"""
        if self.syncing:
            return

        enabled = (state == Qt.Checked)

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    # Update flags field: set or clear bit 1
                    if enabled:
                        self.per_key_values[layer][key_index]['flags'] |= 0x02  # Set bit 1
                    else:
                        self.per_key_values[layer][key_index]['flags'] &= ~0x02  # Clear bit 1

                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        # Enable/disable velocity curve dropdown based on this flag
        self.velocity_curve_combo.setEnabled(enabled)
        self.refresh_layer_display()

    def send_layer_actuation(self, layer):
        """Send layer actuation settings to device"""
        data = self.layer_data[layer]

        # Build flags byte (no velocity curve flag - that's now per-key)
        flags = 0
        # Bit 2 (use_fixed_velocity) is set in the actuation settings tab, not here

        # Build payload: [layer, normal, midi, velocity, vel_speed, flags] (6 bytes)
        payload = bytes([
            layer,
            data['normal'],
            data['midi'],
            data['velocity'],
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

        # Toggle between global and per-key actuation sliders only
        self.global_actuation_widget.setVisible(not self.mode_enabled)
        self.per_key_actuation_widget.setVisible(self.mode_enabled)

        # Load appropriate values for the visible widget
        if not self.mode_enabled:
            # Load global actuation values
            self.load_global_actuation()

        # Update enabled state of trigger slider when in per-key mode
        if self.mode_enabled:
            key_selected = self.container.active_key is not None
            self.trigger_slider.setEnabled(key_selected)

        # Update device
        if self.device and isinstance(self.device, VialKeyboard):
            self.device.keyboard.set_per_key_mode(self.mode_enabled, self.per_layer_enabled)

        self.refresh_layer_display()

    def update_slider_states(self):
        """Update slider visibility based on per-key mode (no-op since we removed old sliders)"""
        # All controls are now in the per-key settings tab
        pass

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

            # Copy in memory (deep copy of dicts)
            for key_index in range(70):
                self.per_key_values[dest_layer][key_index] = self.per_key_values[source_layer][key_index].copy()

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
                    # Copy in memory (deep copy of dicts)
                    for key_index in range(70):
                        self.per_key_values[dest_layer][key_index] = self.per_key_values[source_layer][key_index].copy()

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
            # Reset in memory to defaults (deadzones always enabled)
            for layer in range(12):
                for key_index in range(70):
                    self.per_key_values[layer][key_index] = {
                        'actuation': 60,                    # 1.5mm
                        'deadzone_top': 4,                  # 0.1mm from right
                        'deadzone_bottom': 4,               # 0.1mm from left
                        'velocity_curve': 2,                # Medium
                        'flags': 0,                         # Both rapidfire and per-key velocity curve disabled
                        'rapidfire_press_sens': 4,          # 0.1mm from left
                        'rapidfire_release_sens': 4,        # 0.1mm from right
                        'rapidfire_velocity_mod': 0         # No modifier
                    }

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

        # Load global actuation values if per-key mode is disabled
        if not self.mode_enabled:
            self.load_global_actuation()

    def load_global_actuation(self):
        """Load global actuation values from layer_data"""
        if not self.valid():
            return

        self.syncing = True

        # Get layer to use
        layer = self.current_layer if self.per_layer_enabled else 0

        # Load normal and MIDI actuation values
        self.global_normal_slider.setValue(self.layer_data[layer]['normal'])
        self.global_normal_value_label.setText(self.value_to_mm(self.layer_data[layer]['normal']))

        self.global_midi_slider.setValue(self.layer_data[layer]['midi'])
        self.global_midi_value_label.setText(self.value_to_mm(self.layer_data[layer]['midi']))

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

            # Load all per-key values from device (now returns dict with 8 fields)
            # If communication fails or returns None, set safe defaults
            communication_failed = False
            try:
                for layer in range(12):
                    for key_index in range(70):
                        settings = self.keyboard.get_per_key_actuation(layer, key_index)
                        if settings is not None:
                            # get_per_key_actuation now returns a dict with all 8 fields
                            self.per_key_values[layer][key_index] = settings
                        else:
                            communication_failed = True
                            break
                    if communication_failed:
                        break
            except Exception as e:
                print(f"Error loading per-key actuations from device: {e}")
                communication_failed = True

            # If communication failed, set all keys to safe defaults
            if communication_failed:
                print("Setting all keys to safe defaults: 0.1mm deadzones, 2.0mm actuation")
                for layer in range(12):
                    for key_index in range(70):
                        self.per_key_values[layer][key_index] = {
                            'actuation': 80,                    # 2.0mm (80/40 = 2.0)
                            'deadzone_top': 4,                  # 0.1mm from right
                            'deadzone_bottom': 4,               # 0.1mm from left
                            'velocity_curve': 2,                # Medium
                            'flags': 0,                         # All disabled
                            'rapidfire_press_sens': 4,          # 0.1mm from left
                            'rapidfire_release_sens': 4,        # 0.1mm from right
                            'rapidfire_velocity_mod': 0         # No modifier
                        }

            # Load layer actuation data from device (6 bytes per layer)
            try:
                for layer in range(12):
                    data = self.keyboard.get_layer_actuation(layer)
                    if data:
                        self.layer_data[layer] = {
                            'normal': data['normal'],
                            'midi': data['midi'],
                            'velocity': data['velocity'],
                            'vel_speed': data['vel_speed']
                            # Removed: 'use_per_key_velocity_curve' - now per-key
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
                    settings = self.per_key_values[layer][key_index]
                    # Display actuation value as "X.Xmm" on the key
                    key.setText(self.value_to_mm(settings['actuation']))
                else:
                    key.setText("")

        self.container.update()

    def on_select_all(self):
        """Handle Select All button click"""
        self.container.select_all()

    def on_unselect_all(self):
        """Handle Unselect All button click"""
        self.container.unselect_all()

    def on_invert_selection(self):
        """Handle Invert Selection button click"""
        self.container.invert_selection()

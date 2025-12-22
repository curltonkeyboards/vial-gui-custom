# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtWidgets import (QHBoxLayout, QLabel, QVBoxLayout, QMessageBox, QWidget,
                              QSlider, QCheckBox, QPushButton, QComboBox, QFrame,
                              QSizePolicy, QScrollArea)
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

        # Cache for per-key actuation values (70 keys × 12 layers)
        self.per_key_values = []
        for layer in range(12):
            self.per_key_values.append([60] * 70)  # Default: 60 = 1.5mm

        # Mode flags
        self.mode_enabled = False
        self.per_layer_enabled = False

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
        """Create the bottom control panel with checkboxes, slider, and buttons"""
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        panel.setMaximumHeight(200)
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 10, 20, 10)

        # Checkboxes row
        checkbox_row = QHBoxLayout()

        self.enable_checkbox = QCheckBox(tr("TriggerSettings", "Enable Per-Key Actuation"))
        self.enable_checkbox.setStyleSheet("QCheckBox { font-weight: bold; }")
        self.enable_checkbox.stateChanged.connect(self.on_enable_changed)
        checkbox_row.addWidget(self.enable_checkbox)

        self.per_layer_checkbox = QCheckBox(tr("TriggerSettings", "Per-Layer Mode"))
        self.per_layer_checkbox.setEnabled(False)
        self.per_layer_checkbox.stateChanged.connect(self.on_per_layer_changed)
        checkbox_row.addWidget(self.per_layer_checkbox)

        checkbox_row.addStretch()
        layout.addLayout(checkbox_row)

        # Actuation slider
        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(10)

        actuation_label = QLabel(tr("TriggerSettings", "Actuation:"))
        actuation_label.setMinimumWidth(80)
        slider_layout.addWidget(actuation_label)

        self.actuation_slider = QSlider(Qt.Horizontal)
        self.actuation_slider.setMinimum(0)
        self.actuation_slider.setMaximum(100)
        self.actuation_slider.setValue(60)
        self.actuation_slider.setEnabled(False)
        self.actuation_slider.valueChanged.connect(self.on_slider_changed)
        slider_layout.addWidget(self.actuation_slider, 1)

        self.actuation_value_label = QLabel("1.5mm")
        self.actuation_value_label.setMinimumWidth(60)
        self.actuation_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 14px; }")
        self.actuation_value_label.setAlignment(Qt.AlignCenter)
        slider_layout.addWidget(self.actuation_value_label)

        layout.addLayout(slider_layout)

        # Buttons row
        button_row = QHBoxLayout()

        self.copy_layer_btn = QPushButton(tr("TriggerSettings", "Copy from Layer..."))
        self.copy_layer_btn.setEnabled(False)
        self.copy_layer_btn.clicked.connect(self.on_copy_layer)
        button_row.addWidget(self.copy_layer_btn)

        self.reset_btn = QPushButton(tr("TriggerSettings", "Reset All to Default"))
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self.on_reset_all)
        button_row.addWidget(self.reset_btn)

        button_row.addStretch()
        layout.addLayout(button_row)

        panel.setLayout(layout)
        return panel

    def value_to_mm(self, value):
        """Convert 0-100 value to millimeters string"""
        mm = (value / 40.0)  # 0-100 maps to 0-2.5mm (100/40 = 2.5)
        return f"{mm:.1f}mm"

    def on_empty_space_clicked(self):
        """Deselect key when clicking empty space"""
        self.container.deselect()
        self.container.update()

    def on_key_clicked(self, key):
        """Handle key click - load its actuation value"""
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

    def on_slider_changed(self, value):
        """Handle slider value change"""
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

    def on_enable_changed(self, state):
        """Handle enable checkbox toggle"""
        if self.syncing:
            return

        self.mode_enabled = (state == Qt.Checked)
        self.per_layer_checkbox.setEnabled(self.mode_enabled)
        self.copy_layer_btn.setEnabled(self.mode_enabled)
        self.reset_btn.setEnabled(self.mode_enabled)

        # Update device
        if self.device and isinstance(self.device, VialKeyboard):
            self.device.keyboard.set_per_key_mode(self.mode_enabled, self.per_layer_enabled)

        self.refresh_layer_display()

    def on_per_layer_changed(self, state):
        """Handle per-layer checkbox toggle"""
        if self.syncing:
            return

        self.per_layer_enabled = (state == Qt.Checked)

        # Update device
        if self.device and isinstance(self.device, VialKeyboard):
            self.device.keyboard.set_per_key_mode(self.mode_enabled, self.per_layer_enabled)

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
        self.refresh_layer_display()

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
                self.per_layer_checkbox.setEnabled(self.mode_enabled)
                self.copy_layer_btn.setEnabled(self.mode_enabled)
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

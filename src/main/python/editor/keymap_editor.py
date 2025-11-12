# SPDX-License-Identifier: GPL-2.0-or-later
import json

from PyQt5.QtWidgets import (QHBoxLayout, QLabel, QVBoxLayout, QMessageBox, QWidget,
                              QGroupBox, QSlider, QCheckBox, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal

from any_keycode_dialog import AnyKeycodeDialog
from editor.basic_editor import BasicEditor
from widgets.keyboard_widget import KeyboardWidget2, EncoderWidget, EncoderWidget2
from keycodes.keycodes import Keycode
from widgets.square_button import SquareButton
from tabbed_keycodes import TabbedKeycodes, keycode_filter_masked
from util import tr, KeycodeDisplay
from vial_device import VialKeyboard


class QuickActuationWidget(QGroupBox):
    """Compact actuation controls for quick access in keymap editor"""
    
    show_advanced_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__(tr("QuickActuationWidget", "Quick Actuation"))
        
        self.device = None
        self.syncing = False
        
        self.setMaximumWidth(250)
        self.setStyleSheet("QGroupBox { font-weight: bold; font-size: 11px; }")
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 15, 10, 10)
        self.setLayout(layout)
        
        # Normal Keys Actuation slider
        slider_layout = QHBoxLayout()
        label = QLabel(tr("QuickActuationWidget", "Actuation:"))
        label.setMinimumWidth(70)
        slider_layout.addWidget(label)
        
        self.normal_slider = QSlider(Qt.Horizontal)
        self.normal_slider.setMinimum(0)
        self.normal_slider.setMaximum(100)
        self.normal_slider.setValue(80)
        slider_layout.addWidget(self.normal_slider)
        
        self.normal_value_label = QLabel("2.00mm")
        self.normal_value_label.setMinimumWidth(50)
        self.normal_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9px; }")
        slider_layout.addWidget(self.normal_value_label)
        
        layout.addLayout(slider_layout)
        self.normal_slider.valueChanged.connect(self.on_slider_changed)
        
        # Enable Rapidfire checkbox
        self.rapid_checkbox = QCheckBox(tr("QuickActuationWidget", "Enable Rapidfire"))
        self.rapid_checkbox.setStyleSheet("QCheckBox { font-size: 10px; }")
        self.rapid_checkbox.setChecked(False)
        layout.addWidget(self.rapid_checkbox)
        self.rapid_checkbox.stateChanged.connect(self.on_rapidfire_toggled)
        
        # Rapidfire Sensitivity slider (hidden by default)
        rapid_slider_layout = QHBoxLayout()
        rapid_label = QLabel(tr("QuickActuationWidget", "Sensitivity:"))
        rapid_label.setMinimumWidth(70)
        rapid_slider_layout.addWidget(rapid_label)
        
        self.rapid_slider = QSlider(Qt.Horizontal)
        self.rapid_slider.setMinimum(1)
        self.rapid_slider.setMaximum(100)
        self.rapid_slider.setValue(4)
        rapid_slider_layout.addWidget(self.rapid_slider)
        
        self.rapid_value_label = QLabel("4")
        self.rapid_value_label.setMinimumWidth(50)
        self.rapid_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9px; }")
        rapid_slider_layout.addWidget(self.rapid_value_label)
        
        self.rapid_widget = QWidget()
        self.rapid_widget.setLayout(rapid_slider_layout)
        self.rapid_widget.setVisible(False)
        layout.addWidget(self.rapid_widget)
        
        self.rapid_slider.valueChanged.connect(self.on_rapid_slider_changed)
        
        layout.addStretch()
        
        # Buttons at the bottom
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(5)
        
        self.advanced_btn = QPushButton(tr("QuickActuationWidget", "Show Advanced Options"))
        self.advanced_btn.setMaximumHeight(30)
        self.advanced_btn.clicked.connect(self.on_show_advanced)
        buttons_layout.addWidget(self.advanced_btn)
        
        self.save_btn = QPushButton(tr("QuickActuationWidget", "Save"))
        self.save_btn.setMaximumHeight(30)
        self.save_btn.clicked.connect(self.on_save)
        buttons_layout.addWidget(self.save_btn)
        
        layout.addLayout(buttons_layout)
    
    def on_slider_changed(self, value):
        """Handle normal actuation slider change"""
        self.normal_value_label.setText(f"{value * 0.025:.2f}mm")
    
    def on_rapid_slider_changed(self, value):
        """Handle rapidfire sensitivity slider change"""
        self.rapid_value_label.setText(str(value))
    
    def on_rapidfire_toggled(self, state):
        """Show/hide rapidfire sensitivity slider"""
        self.rapid_widget.setVisible(state == Qt.Checked)
    
    def on_show_advanced(self):
        """Signal that advanced options should be shown"""
        self.show_advanced_requested.emit()
    
    def on_save(self):
        """Save current actuation settings to keyboard"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")
            
            # Get current values
            normal_value = self.normal_slider.value()
            rapid_enabled = self.rapid_checkbox.isChecked()
            rapid_value = self.rapid_slider.value()
            
            # Build flags
            flags = 0
            if rapid_enabled:
                flags |= 0x01
            
            # Send to all 12 layers with same values
            # Using default values for advanced options
            for layer in range(12):
                data = bytearray([
                    layer,
                    normal_value,  # normal actuation
                    normal_value,  # midi actuation (same as normal)
                    0,  # aftertouch mode (off)
                    2,  # velocity mode (speed-based)
                    rapid_value,  # rapidfire sensitivity
                    10,  # midi rapidfire sensitivity
                    10,  # midi rapidfire velocity range
                    10,  # velocity speed scale
                    74,  # aftertouch cc
                    flags  # flags byte
                ])
                
                if not self.device.keyboard.set_layer_actuation(data):
                    raise RuntimeError(f"Failed to set actuation for layer {layer}")
            
            QMessageBox.information(None, "Success", 
                "Quick actuation settings saved successfully!")
                
        except Exception as e:
            QMessageBox.critical(None, "Error", 
                f"Failed to save actuation settings: {str(e)}")
    
    def set_device(self, device):
        """Set the device and load current settings"""
        self.device = device
        self.setEnabled(isinstance(device, VialKeyboard))
        
        if self.device and isinstance(self.device, VialKeyboard):
            self.load_from_device()
    
    def load_from_device(self):
        """Load current actuation settings from device"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                return
            
            actuations = self.device.keyboard.get_all_layer_actuations()
            
            if not actuations or len(actuations) != 120:
                return
            
            self.syncing = True
            
            # Load from layer 0
            normal_value = actuations[0]
            rapid_value = actuations[4]
            flags = actuations[9]
            rapid_enabled = (flags & 0x01) != 0
            
            self.normal_slider.setValue(normal_value)
            self.rapid_slider.setValue(rapid_value)
            self.rapid_checkbox.setChecked(rapid_enabled)
            self.rapid_widget.setVisible(rapid_enabled)
            
            self.syncing = False
            
        except Exception:
            self.syncing = False
    
    def sync_from_configurator(self, normal, rapid_enabled, rapid):
        """Sync values from main configurator"""
        if self.syncing:
            return
        
        self.syncing = True
        self.normal_slider.setValue(normal)
        self.rapid_checkbox.setChecked(rapid_enabled)
        self.rapid_slider.setValue(rapid)
        self.rapid_widget.setVisible(rapid_enabled)
        self.syncing = False
    
    def get_values(self):
        """Get current values for syncing to main configurator"""
        return {
            'normal': self.normal_slider.value(),
            'rapid_enabled': self.rapid_checkbox.isChecked(),
            'rapid': self.rapid_slider.value()
        }


class ClickableWidget(QWidget):

    clicked = pyqtSignal()

    def mousePressEvent(self, evt):
        super().mousePressEvent(evt)
        self.clicked.emit()


class KeymapEditor(BasicEditor):
    
    # Signal to request tab switch to actuation configurator
    switch_to_actuation = pyqtSignal(bool)  # bool = enable advanced mode

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
        self.quick_actuation.show_advanced_requested.connect(self.on_show_advanced_actuation)
        
        # contains the actual keyboard
        self.container = KeyboardWidget2(layout_editor)
        self.container.clicked.connect(self.on_key_clicked)
        self.container.deselected.connect(self.on_key_deselected)

        # Layout with quick actuation on the left and keyboard on the right
        keyboard_layout = QHBoxLayout()
        keyboard_layout.addWidget(self.quick_actuation, 0, Qt.AlignTop)
        keyboard_layout.addWidget(self.container, 1, Qt.AlignHCenter)

        layout = QVBoxLayout()
        layout.addLayout(layout_labels_container)
        layout.addLayout(keyboard_layout)
        
        w = ClickableWidget()
        w.setLayout(layout)
        w.clicked.connect(self.on_empty_space_clicked)

        self.layer_buttons = []
        self.keyboard = None
        self.current_layer = 0

        layout_editor.changed.connect(self.on_layout_changed)

        self.container.anykey.connect(self.on_any_keycode)

        self.tabbed_keycodes = TabbedKeycodes()
        self.tabbed_keycodes.keycode_changed.connect(self.on_keycode_changed)
        self.tabbed_keycodes.anykey.connect(self.on_any_keycode)

        self.addWidget(w)
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
            
        # Set device for quick actuation widget
        self.quick_actuation.set_device(device)
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
    
    def on_show_advanced_actuation(self):
        """Request to switch to actuation configurator tab with advanced options enabled"""
        self.switch_to_actuation.emit(True)
    
    def sync_quick_actuation(self, normal, rapid_enabled, rapid):
        """Sync quick actuation widget from main configurator"""
        self.quick_actuation.sync_from_configurator(normal, rapid_enabled, rapid)
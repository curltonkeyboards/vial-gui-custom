# SPDX-License-Identifier: GPL-2.0-or-later
import math
import struct
import json

from PyQt5.QtWidgets import (QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QLabel,
                           QSizePolicy, QGroupBox, QGridLayout, QComboBox, QCheckBox,
                           QTableWidget, QHeaderView, QMessageBox, QFileDialog, QFrame,
                           QScrollArea, QSlider)
from PyQt5.QtCore import Qt, QTimer
from PyQt5 import QtCore
from PyQt5.QtGui import QPainterPath, QRegion

from widgets.combo_box import ArrowComboBox
from editor.basic_editor import BasicEditor
from protocol.constants import VIAL_PROTOCOL_MATRIX_TESTER
from tabbed_keycodes import GamepadWidget, DpadButton
from protocol.keyboard_comm import (
    PARAM_CHANNEL_NUMBER, PARAM_TRANSPOSE_NUMBER, PARAM_TRANSPOSE_NUMBER2, PARAM_TRANSPOSE_NUMBER3,
    PARAM_HE_VELOCITY_CURVE, PARAM_HE_VELOCITY_MIN, PARAM_HE_VELOCITY_MAX,
    PARAM_KEYSPLIT_HE_VELOCITY_CURVE, PARAM_KEYSPLIT_HE_VELOCITY_MIN, PARAM_KEYSPLIT_HE_VELOCITY_MAX,
    PARAM_TRIPLESPLIT_HE_VELOCITY_CURVE, PARAM_TRIPLESPLIT_HE_VELOCITY_MIN, PARAM_TRIPLESPLIT_HE_VELOCITY_MAX,
    PARAM_AFTERTOUCH_MODE, PARAM_AFTERTOUCH_CC,
    PARAM_BASE_SUSTAIN, PARAM_KEYSPLIT_SUSTAIN, PARAM_TRIPLESPLIT_SUSTAIN,
    PARAM_KEYSPLITCHANNEL, PARAM_KEYSPLIT2CHANNEL, PARAM_KEYSPLITSTATUS,
    PARAM_KEYSPLITTRANSPOSESTATUS, PARAM_KEYSPLITVELOCITYSTATUS
)
from widgets.keyboard_widget import KeyboardWidget2, KeyboardWidgetSimple
from util import tr
from vial_device import VialKeyboard
from unlocker import Unlocker


class MatrixTest(BasicEditor):

    def __init__(self, layout_editor):
        super().__init__()

        self.layout_editor = layout_editor

        self.KeyboardWidget2 = KeyboardWidgetSimple(layout_editor)
        self.KeyboardWidget2.set_enabled(False)

        self.unlock_btn = QPushButton("Unlock")
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setMinimumHeight(30)
        self.reset_btn.setMaximumHeight(30)
        self.reset_btn.setMinimumWidth(80)
        self.reset_btn.setStyleSheet("QPushButton { border-radius: 5px; }")

        layout = QVBoxLayout()
        layout.addWidget(self.KeyboardWidget2)
        layout.setAlignment(self.KeyboardWidget2, Qt.AlignCenter)

        self.addLayout(layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.unlock_lbl = QLabel(tr("MatrixTest", "Unlock the keyboard before testing:"))
        btn_layout.addWidget(self.unlock_lbl)
        btn_layout.addWidget(self.unlock_btn)
        btn_layout.addWidget(self.reset_btn)
        self.addLayout(btn_layout)

        self.keyboard = None
        self.device = None
        self.polling = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.matrix_poller)

        self.unlock_btn.clicked.connect(self.unlock)
        self.reset_btn.clicked.connect(self.reset_keyboard_widget)

        self.grabber = QWidget()

    def rebuild(self, device):
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard

            self.KeyboardWidget2.set_keys(self.keyboard.keys, self.keyboard.encoders)
        self.KeyboardWidget2.setEnabled(self.valid())

    def valid(self):
        # Check if vial protocol is v3 or later
        return isinstance(self.device, VialKeyboard) and \
               (self.device.keyboard and self.device.keyboard.vial_protocol >= VIAL_PROTOCOL_MATRIX_TESTER) and \
               ((self.device.keyboard.cols // 8 + 1) * self.device.keyboard.rows <= 28)

    def reset_keyboard_widget(self):
        # reset keyboard widget
        for w in self.KeyboardWidget2.widgets:
            w.setPressed(False)
            w.setOn(False)

        self.KeyboardWidget2.update_layout()
        self.KeyboardWidget2.update()
        self.KeyboardWidget2.updateGeometry()

    def matrix_poller(self):
        if not self.valid():
            self.timer.stop()
            return

        try:
            unlocked = self.keyboard.get_unlock_status(3)
        except (RuntimeError, ValueError):
            self.timer.stop()
            return

        if not unlocked:
            self.unlock_btn.show()
            self.unlock_lbl.show()
            return

        # we're unlocked, so hide unlock button and label
        self.unlock_btn.hide()
        self.unlock_lbl.hide()

        # Get size for matrix
        rows = self.keyboard.rows
        cols = self.keyboard.cols
        # Generate 2d array of matrix
        matrix = [[None] * cols for x in range(rows)]

        # Get matrix data from keyboard
        try:
            data = self.keyboard.matrix_poll()
        except (RuntimeError, ValueError):
            self.timer.stop()
            return

        # Calculate the amount of bytes belong to 1 row, each bit is 1 key, so per 8 keys in a row,
        # a byte is needed for the row.
        row_size = math.ceil(cols / 8)

        for row in range(rows):
            # Make slice of bytes for the row (skip first 2 bytes, they're for VIAL)
            row_data_start = 2 + (row * row_size)
            row_data_end = row_data_start + row_size
            row_data = data[row_data_start:row_data_end]

            # Get each bit representing pressed state for col
            for col in range(cols):
                # row_data is array of bytes, calculate in which byte the col is located
                col_byte = len(row_data) - 1 - math.floor(col / 8)
                # since we select a single byte as slice of byte, mod 8 to get nth pos of byte
                col_mod = (col % 8)
                # write to matrix array
                matrix[row][col] = (row_data[col_byte] >> col_mod) & 1

        # write matrix state to keyboard widget
        for w in self.KeyboardWidget2.widgets:
            if w.desc.row is not None and w.desc.col is not None:
                row = w.desc.row
                col = w.desc.col

                if row < len(matrix) and col < len(matrix[row]):
                    w.setPressed(matrix[row][col])
                    if matrix[row][col]:
                        w.setOn(True)

        self.KeyboardWidget2.update_layout()
        self.KeyboardWidget2.update()
        self.KeyboardWidget2.updateGeometry()

    def unlock(self):
        Unlocker.unlock(self.keyboard)

    def activate(self):
        self.grabber.grabKeyboard()
        self.timer.start(20)

    def deactivate(self):
        self.grabber.releaseKeyboard()
        self.timer.stop()


class ThruLoopConfigurator(BasicEditor):
    
    def __init__(self):
        super().__init__()
        
        self.single_loopchop_label = None
        self.master_cc = None
        self.single_loopchop_widgets = []
        self.nav_widget = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create scroll area for better window resizing
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        scroll_area.setWidget(main_widget)
        self.addWidget(scroll_area, 1)

        # Top row: Basic Settings and LoopChop side by side
        top_row_layout = QHBoxLayout()
        main_layout.addLayout(top_row_layout)
        
        # Basic Settings Group
        self.basic_group = QGroupBox(tr("ThruLoopConfigurator", "Basic Settings"))
        basic_layout = QGridLayout()
        self.basic_group.setLayout(basic_layout)
        top_row_layout.addWidget(self.basic_group)
        
        # ThruLoop Channel
        basic_layout.addWidget(QLabel(tr("ThruLoopConfigurator", "ThruLoop Channel")), 0, 0)
        self.loop_channel = ArrowComboBox()
        self.loop_channel.setMinimumWidth(150)
        self.loop_channel.setMaximumHeight(30)
        self.loop_channel.setEditable(True)
        self.loop_channel.lineEdit().setReadOnly(True)
        self.loop_channel.lineEdit().setAlignment(Qt.AlignCenter)
        for i in range(1, 17):
            self.loop_channel.addItem(f"Channel {i}", i)
        self.loop_channel.setCurrentIndex(15)
        basic_layout.addWidget(self.loop_channel, 0, 1)
        
        # Send Restart Messages and Alternate Restart Mode (side by side)
        basic_layout.addWidget(QLabel(tr("ThruLoopConfigurator", "Restart Settings:")), 1, 0, 1, 2)
        
        self.sync_midi = QCheckBox(tr("ThruLoopConfigurator", "Send Restart Messages"))
        basic_layout.addWidget(self.sync_midi, 2, 0)
        
        self.alternate_restart = QCheckBox(tr("ThruLoopConfigurator", "Alternate Restart Mode"))
        basic_layout.addWidget(self.alternate_restart, 2, 1)
        
        # Disable ThruLoop and CC Loop Recording (side by side)
        basic_layout.addWidget(QLabel(tr("ThruLoopConfigurator", "Loop Controls:")), 3, 0, 1, 2)
        
        self.loop_enabled = QCheckBox(tr("ThruLoopConfigurator", "Disable ThruLoop"))
        basic_layout.addWidget(self.loop_enabled, 4, 0)
        
        self.cc_loop_recording = QCheckBox(tr("ThruLoopConfigurator", "CC Loop Recording"))
        basic_layout.addWidget(self.cc_loop_recording, 4, 1)
        
        # LoopChop Settings (more compact)
        self.loopchop_group = QGroupBox(tr("ThruLoopConfigurator", "LoopChop"))
        loopchop_layout = QGridLayout()
        loopchop_layout.setSpacing(5)
        loopchop_layout.setContentsMargins(10, 10, 10, 10)
        self.loopchop_group.setLayout(loopchop_layout)
        top_row_layout.addWidget(self.loopchop_group)
        
        # Separate CCs for LoopChop checkbox
        self.separate_loopchop = QCheckBox(tr("ThruLoopConfigurator", "Separate CCs for LoopChop"))
        loopchop_layout.addWidget(self.separate_loopchop, 0, 0, 1, 4)
        
        # Single LoopChop CC - Always visible
        self.single_loopchop_label = QLabel(tr("ThruLoopConfigurator", "Loop Chop"))
        loopchop_layout.addWidget(self.single_loopchop_label, 1, 0)
        self.master_cc = self.create_cc_combo()
        loopchop_layout.addWidget(self.master_cc, 1, 1, 1, 3)
        
        # Individual LoopChop CCs (8 navigation CCs) - More compact layout
        nav_layout = QGridLayout()
        nav_layout.setSpacing(3)
        self.nav_combos = []
        for i in range(8):
            row = i // 4
            col = i % 4
            label = QLabel(f"{i}/8")
            label.setMaximumWidth(30)
            nav_layout.addWidget(label, row * 2, col)
            combo = self.create_cc_combo()
            nav_layout.addWidget(combo, row * 2 + 1, col)
            self.nav_combos.append(combo)
        
        self.nav_widget = QWidget()
        self.nav_widget.setLayout(nav_layout)
        loopchop_layout.addWidget(self.nav_widget, 2, 0, 1, 4)
        
        # Main Functions - Using clean grid layout
        self.main_group = QGroupBox(tr("ThruLoopConfigurator", "Main Functions"))
        self.main_group.setMaximumWidth(700)
        main_layout.addWidget(self.main_group, alignment=QtCore.Qt.AlignHCenter)
        main_grid = QGridLayout()
        main_grid.setSpacing(8)
        main_grid.setContentsMargins(10, 15, 10, 10)
        self.main_group.setLayout(main_grid)

        # Add column headers
        for col in range(4):
            header = QLabel(f"Loop {col + 1}")
            header.setAlignment(QtCore.Qt.AlignCenter)
            header.setStyleSheet("font-weight: bold;")
            main_grid.addWidget(header, 0, col + 1)

        # Add function rows
        functions = ["Start Recording", "Stop Recording", "Start Playing", "Stop Playing", "Clear", "Restart"]
        self.main_combos = []
        for row_idx, func_name in enumerate(functions):
            # Row label
            label = QLabel(func_name)
            label.setStyleSheet("font-weight: bold;")
            main_grid.addWidget(label, row_idx + 1, 0)

            # Combo boxes for each loop
            row_combos = []
            for col_idx in range(4):
                combo = self.create_cc_combo(for_table=True)
                main_grid.addWidget(combo, row_idx + 1, col_idx + 1)
                row_combos.append(combo)
            self.main_combos.append(row_combos)
        
        # Overdub Functions - Using clean grid layout
        self.overdub_group = QGroupBox(tr("ThruLoopConfigurator", "Overdub Functions"))
        self.overdub_group.setMaximumWidth(700)
        main_layout.addWidget(self.overdub_group, alignment=QtCore.Qt.AlignHCenter)
        overdub_grid = QGridLayout()
        overdub_grid.setSpacing(8)
        overdub_grid.setContentsMargins(10, 15, 10, 10)
        self.overdub_group.setLayout(overdub_grid)

        # Add column headers
        for col in range(4):
            header = QLabel(f"Overdub {col + 1}")
            header.setAlignment(QtCore.Qt.AlignCenter)
            header.setStyleSheet("font-weight: bold;")
            overdub_grid.addWidget(header, 0, col + 1)

        # Add function rows (same as main functions)
        self.overdub_combos = []
        for row_idx, func_name in enumerate(functions):
            # Row label
            label = QLabel(func_name)
            label.setStyleSheet("font-weight: bold;")
            overdub_grid.addWidget(label, row_idx + 1, 0)

            # Combo boxes for each loop
            row_combos = []
            for col_idx in range(4):
                combo = self.create_cc_combo(for_table=True)
                overdub_grid.addWidget(combo, row_idx + 1, col_idx + 1)
                row_combos.append(combo)
            self.overdub_combos.append(row_combos)
        
        # Buttons
        self.addStretch()
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        # Button style - bigger and less rounded
        button_style = "QPushButton { border-radius: 3px; padding: 8px 16px; }"

        save_btn = QPushButton(tr("ThruLoopConfigurator", "Save Configuration"))
        save_btn.setMinimumHeight(45)
        save_btn.setMinimumWidth(200)
        save_btn.setStyleSheet(button_style)
        save_btn.clicked.connect(self.on_save)
        buttons_layout.addWidget(save_btn)

        load_btn = QPushButton(tr("ThruLoopConfigurator", "Load from Keyboard"))
        load_btn.setMinimumHeight(45)
        load_btn.setMinimumWidth(210)
        load_btn.setStyleSheet(button_style)
        load_btn.clicked.connect(self.on_load_from_keyboard)
        buttons_layout.addWidget(load_btn)

        reset_btn = QPushButton(tr("ThruLoopConfigurator", "Reset to Defaults"))
        reset_btn.setMinimumHeight(45)
        reset_btn.setMinimumWidth(180)
        reset_btn.setStyleSheet(button_style)
        reset_btn.clicked.connect(self.on_reset)
        buttons_layout.addWidget(reset_btn)

        self.addLayout(buttons_layout)
        
        # Apply stylesheet to prevent bold focus styling and center combo box text
        main_widget.setStyleSheet("""
            QCheckBox:focus {
                font-weight: normal;
                outline: none;
            }
            QPushButton:focus {
                font-weight: normal;
                outline: none;
            }
            QComboBox {
                text-align: center;
            }
            QComboBox:focus {
                font-weight: normal;
                outline: none;
            }
        """)
        
        # Connect signals AFTER all widgets are created
        self.loop_enabled.stateChanged.connect(self.on_loop_enabled_changed)
        self.separate_loopchop.stateChanged.connect(self.on_separate_loopchop_changed)
        
        # Initialize UI state AFTER all widgets and connections are set up
        self.on_loop_enabled_changed()
        self.on_separate_loopchop_changed()
        
    def create_cc_combo(self, for_table=False):
        """Create a CC selector combobox
        
        Args:
            for_table: If True, creates a narrower combo for use in tables
        """
        combo = ArrowComboBox()
        if for_table:
            combo.setMaximumWidth(100)  # Narrower for tables to show arrow
        else:
            combo.setMinimumWidth(120)
        combo.setMaximumHeight(30)
        combo.setEditable(True)
        combo.lineEdit().setReadOnly(True)
        combo.lineEdit().setAlignment(Qt.AlignCenter)

        # Add "None" option
        combo.addItem("None", 128)

        # Add CC options
        for cc_num in range(128):
            combo.addItem(f"CC# {cc_num}", cc_num)

        combo.setCurrentIndex(0)
        return combo
    
    def get_cc_value(self, combo):
        """Get the current CC value from a CC combo"""
        return combo.currentData()
    
    def set_cc_value(self, combo, value):
        """Set the CC value for a combo"""
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return
        combo.setCurrentIndex(0)
    
    def on_loop_enabled_changed(self):
        enabled = not self.loop_enabled.isChecked()
        self.main_group.setEnabled(enabled)
        self.overdub_group.setEnabled(enabled) 
        self.loopchop_group.setEnabled(enabled)
    
    def on_separate_loopchop_changed(self):
        separate = self.separate_loopchop.isChecked()
        if self.single_loopchop_label:
            self.single_loopchop_label.setEnabled(not separate)
        if self.master_cc:
            self.master_cc.setEnabled(not separate)
        if self.nav_widget:
            self.nav_widget.setEnabled(separate)
    
    def get_combos_cc_values(self, combos_array):
        """Get CC values from a 2D array of combos"""
        values = []
        for row_combos in combos_array:
            for combo in row_combos:
                values.append(self.get_cc_value(combo))
        return values

    def set_combos_cc_values(self, combos_array, values):
        """Set CC values to a 2D array of combos"""
        idx = 0
        for row_combos in combos_array:
            for combo in row_combos:
                if idx < len(values):
                    self.set_cc_value(combo, values[idx])
                    idx += 1
    
    def get_restart_cc_values(self):
        """Get restart CCs from the main combos (last row)"""
        restart_values = []
        for col in range(4):
            combo = self.main_combos[5][col]  # Row 5 is "Restart"
            restart_values.append(self.get_cc_value(combo))
        return restart_values

    def set_restart_cc_values(self, values):
        """Set restart CCs in the main combos (last row)"""
        for col in range(4):
            if col < len(values):
                combo = self.main_combos[5][col]  # Row 5 is "Restart"
                self.set_cc_value(combo, values[col])
    
    def on_save(self):
        """Save all configuration to keyboard"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")
            
            # 1. Send basic loop configuration
            loop_config_data = [
                0 if self.loop_enabled.isChecked() else 1,
                self.loop_channel.currentData(),
                1 if self.sync_midi.isChecked() else 0,
                1 if self.alternate_restart.isChecked() else 0,
            ]
            # Add restart CCs from main table
            restart_values = self.get_restart_cc_values()
            loop_config_data.extend(restart_values)
            # Add CC loop recording
            loop_config_data.append(1 if self.cc_loop_recording.isChecked() else 0)
            
            if not self.device.keyboard.set_thruloop_config(loop_config_data):
                raise RuntimeError("Failed to set ThruLoop config")
            
            # 2. Send main loop CCs (excluding restart row - first 5 rows only)
            main_values = self.get_combos_cc_values(self.main_combos[:5])  # First 5 rows

            if not self.device.keyboard.set_thruloop_main_ccs(main_values):
                raise RuntimeError("Failed to set main CCs")

            # 3. Send overdub CCs (all 6 rows - 24 values total)
            overdub_values = self.get_combos_cc_values(self.overdub_combos)
            if not self.device.keyboard.set_thruloop_overdub_ccs(overdub_values):
                raise RuntimeError("Failed to set overdub CCs")
            
            # 4. Send navigation configuration
            nav_config_data = [
                1 if self.separate_loopchop.isChecked() else 0,
                self.get_cc_value(self.master_cc),
            ]
            for combo in self.nav_combos:
                nav_config_data.append(self.get_cc_value(combo))
            
            if not self.device.keyboard.set_thruloop_navigation(nav_config_data):
                raise RuntimeError("Failed to set navigation config")
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save configuration: {str(e)}")   
        
    def on_load_from_keyboard(self):
        """Load configuration from keyboard using multi-packet collection"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")
                
            # Request and collect multi-packet configuration
            config = self.device.keyboard.get_thruloop_config()
            
            if not config:
                raise RuntimeError("Failed to load config from keyboard")
            
            # Apply the configuration to the UI
            self.apply_config(config)
                
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to load from keyboard: {str(e)}")
    
    def apply_config(self, config):
        """Apply configuration dictionary to UI"""
        # Basic settings
        if 'loopEnabled' in config:
            self.loop_enabled.setChecked(not config.get("loopEnabled", True))
        
        if 'loopChannel' in config:
            for i in range(self.loop_channel.count()):
                if self.loop_channel.itemData(i) == config.get("loopChannel", 16):
                    self.loop_channel.setCurrentIndex(i)
                    break
        
        if 'syncMidi' in config:
            self.sync_midi.setChecked(config.get("syncMidi", False))
        if 'alternateRestart' in config:
            self.alternate_restart.setChecked(config.get("alternateRestart", False))
        if 'ccLoopRecording' in config:
            self.cc_loop_recording.setChecked(config.get("ccLoopRecording", False))
        
        # LoopChop settings
        if 'separateLoopChopCC' in config:
            self.separate_loopchop.setChecked(config.get("separateLoopChopCC", False))
        if 'masterCC' in config:
            self.set_cc_value(self.master_cc, config.get("masterCC", 128))
        
        # Set restart CCs
        if 'restartCCs' in config:
            restart_ccs = config.get("restartCCs", [128] * 4)
            self.set_restart_cc_values(restart_ccs)
        
        # Set main combos CCs (first 5 rows only)
        if 'mainCCs' in config:
            main_ccs = config.get("mainCCs", [128] * 20)
            self.set_combos_cc_values(self.main_combos[:5], main_ccs)

        # Set overdub combos CCs (all 6 rows - 24 values)
        if 'overdubCCs' in config:
            overdub_ccs = config.get("overdubCCs", [128] * 24)
            self.set_combos_cc_values(self.overdub_combos, overdub_ccs)
        
        # Set navigation CCs
        if 'navCCs' in config:
            nav_ccs = config.get("navCCs", [128] * 8)
            for i, combo in enumerate(self.nav_combos):
                if i < len(nav_ccs):
                    self.set_cc_value(combo, nav_ccs[i])
        
        # Update UI state
        self.on_loop_enabled_changed()
        self.on_separate_loopchop_changed()
        
    def on_reset(self):
        """Reset ThruLoop configuration to defaults"""
        try:
            reply = QMessageBox.question(None, "Confirm Reset", 
                                       "Reset ThruLoop configuration to defaults? This cannot be undone.",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                if not self.device or not isinstance(self.device, VialKeyboard):
                    raise RuntimeError("Device not connected")
                    
                if not self.device.keyboard.reset_thruloop_config():
                    raise RuntimeError("Failed to reset ThruLoop config")
                    
                self.reset_ui_to_defaults()
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to reset configuration: {str(e)}")
    
    def reset_ui_to_defaults(self):
        """Reset UI to default values"""
        self.loop_enabled.setChecked(False)
        self.loop_channel.setCurrentIndex(15)
        self.sync_midi.setChecked(False)
        self.alternate_restart.setChecked(False)
        self.cc_loop_recording.setChecked(False)
        self.separate_loopchop.setChecked(False)
        self.set_cc_value(self.master_cc, 128)
        
        # Reset all combos to None (128)
        for row_combos in self.main_combos:
            for combo in row_combos:
                self.set_cc_value(combo, 128)

        for row_combos in self.overdub_combos:
            for combo in row_combos:
                self.set_cc_value(combo, 128)
        
        for combo in self.nav_combos:
            self.set_cc_value(combo, 128)
        
        self.on_loop_enabled_changed()
        self.on_separate_loopchop_changed()
    
    def get_current_config(self):
        """Get current UI configuration as dictionary"""
        config = {
            "version": "1.0",
            "loopEnabled": not self.loop_enabled.isChecked(),
            "loopChannel": self.loop_channel.currentData(), 
            "syncMidi": self.sync_midi.isChecked(),
            "alternateRestart": self.alternate_restart.isChecked(),
            "ccLoopRecording": self.cc_loop_recording.isChecked(),
            "separateLoopChopCC": self.separate_loopchop.isChecked(),
            "masterCC": self.get_cc_value(self.master_cc),
            "restartCCs": self.get_restart_cc_values(),
            "mainCCs": self.get_combos_cc_values(self.main_combos[:5]),  # First 5 rows only
            "overdubCCs": self.get_combos_cc_values(self.overdub_combos),  # All 6 rows - 24 values
            "navCCs": [self.get_cc_value(combo) for combo in self.nav_combos]
        }
        return config
    
    def valid(self):
        return isinstance(self.device, VialKeyboard)

    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return

        # Load ThruLoop configuration from keyboard
        if hasattr(self.device.keyboard, 'thruloop_config') and self.device.keyboard.thruloop_config:
            self.apply_config(self.device.keyboard.thruloop_config)

class MIDIswitchSettingsConfigurator(BasicEditor):
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        # Create scroll area for better window resizing
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        scroll_area.setWidget(main_widget)
        self.addWidget(scroll_area, 1)

        # Global MIDI Settings Group
        global_midi_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "Global MIDI Settings"))
        global_midi_layout = QGridLayout()
        global_midi_layout.setHorizontalSpacing(20)
        global_midi_layout.setVerticalSpacing(10)
        global_midi_layout.setColumnStretch(0, 1)    # Left spacer
        global_midi_layout.setColumnStretch(5, 1)    # Right spacer
        global_midi_group.setLayout(global_midi_layout)
        main_layout.addWidget(global_midi_group)

        row = 0

        # Row 0: Channel and Transpose next to each other
        global_midi_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), row, 1)
        self.global_channel = ArrowComboBox()
        self.global_channel.setMinimumWidth(80)
        self.global_channel.setMinimumHeight(25)
        self.global_channel.setMaximumHeight(25)
        for i in range(16):
            self.global_channel.addItem(f"Channel {i + 1}", i)
        self.global_channel.setCurrentIndex(0)  # Default: Channel 1 (0)
        self.global_channel.setEditable(True)
        self.global_channel.lineEdit().setReadOnly(True)
        self.global_channel.lineEdit().setAlignment(Qt.AlignCenter)
        global_midi_layout.addWidget(self.global_channel, row, 2)

        global_midi_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), row, 3)
        self.global_transpose = ArrowComboBox()
        self.global_transpose.setMinimumWidth(80)
        self.global_transpose.setMinimumHeight(25)
        self.global_transpose.setMaximumHeight(25)
        for i in range(-64, 65):
            self.global_transpose.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.global_transpose.setCurrentIndex(64)  # Default: 0
        self.global_transpose.setEditable(True)
        self.global_transpose.lineEdit().setReadOnly(True)
        self.global_transpose.lineEdit().setAlignment(Qt.AlignCenter)
        global_midi_layout.addWidget(self.global_transpose, row, 4)
        row += 1

        # Row 1: Velocity Curve (always visible)
        self.velocity_curve_label = QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Curve:"))
        global_midi_layout.addWidget(self.velocity_curve_label, row, 1)

        self.global_velocity_curve = ArrowComboBox()
        self.global_velocity_curve.setMinimumWidth(120)
        self.global_velocity_curve.setMinimumHeight(25)
        self.global_velocity_curve.setMaximumHeight(25)
        # Factory curves (0-6)
        self.global_velocity_curve.addItem("Linear", 0)
        self.global_velocity_curve.addItem("Aggro", 1)
        self.global_velocity_curve.addItem("Slow", 2)
        self.global_velocity_curve.addItem("Smooth", 3)
        self.global_velocity_curve.addItem("Steep", 4)
        self.global_velocity_curve.addItem("Instant", 5)
        self.global_velocity_curve.addItem("Turbo", 6)
        # User curves (7-16)
        for i in range(10):
            self.global_velocity_curve.addItem(f"User {i+1}", 7 + i)
        self.global_velocity_curve.setCurrentIndex(0)  # Default: Linear
        self.global_velocity_curve.setEditable(True)
        self.global_velocity_curve.lineEdit().setReadOnly(True)
        self.global_velocity_curve.lineEdit().setAlignment(Qt.AlignCenter)
        global_midi_layout.addWidget(self.global_velocity_curve, row, 2, 1, 3)
        row += 1

        # Row 2: Velocity Min (always visible)
        self.velocity_min_label = QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Min:"))
        global_midi_layout.addWidget(self.velocity_min_label, row, 1)

        self.global_velocity_min = QSlider(Qt.Horizontal)
        self.global_velocity_min.setMinimum(1)
        self.global_velocity_min.setMaximum(127)
        self.global_velocity_min.setValue(1)
        self.global_velocity_min.setMinimumWidth(150)
        global_midi_layout.addWidget(self.global_velocity_min, row, 2, 1, 2)

        self.velocity_min_value_label = QLabel("1")
        self.velocity_min_value_label.setMinimumWidth(30)
        self.velocity_min_value_label.setAlignment(Qt.AlignCenter)
        global_midi_layout.addWidget(self.velocity_min_value_label, row, 4)
        self.global_velocity_min.valueChanged.connect(
            lambda v: self.velocity_min_value_label.setText(str(v))
        )
        row += 1

        # Row 3: Velocity Max (always visible)
        self.velocity_max_label = QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Max:"))
        global_midi_layout.addWidget(self.velocity_max_label, row, 1)

        self.global_velocity_max = QSlider(Qt.Horizontal)
        self.global_velocity_max.setMinimum(1)
        self.global_velocity_max.setMaximum(127)
        self.global_velocity_max.setValue(127)
        self.global_velocity_max.setMinimumWidth(150)
        global_midi_layout.addWidget(self.global_velocity_max, row, 2, 1, 2)

        self.velocity_max_value_label = QLabel("127")
        self.velocity_max_value_label.setMinimumWidth(30)
        self.velocity_max_value_label.setAlignment(Qt.AlignCenter)
        global_midi_layout.addWidget(self.velocity_max_value_label, row, 4)
        self.global_velocity_max.valueChanged.connect(
            lambda v: self.velocity_max_value_label.setText(str(v))
        )
        row += 1

        # Row 4: Sustain (always visible)
        self.sustain_label = QLabel(tr("MIDIswitchSettingsConfigurator", "Sustain:"))
        global_midi_layout.addWidget(self.sustain_label, row, 1)

        self.base_sustain = ArrowComboBox()
        self.base_sustain.setMinimumWidth(120)
        self.base_sustain.setMinimumHeight(25)
        self.base_sustain.setMaximumHeight(25)
        self.base_sustain.addItem("Ignore", 0)
        self.base_sustain.addItem("Allow", 1)
        self.base_sustain.setCurrentIndex(0)  # Default: Ignore
        self.base_sustain.setEditable(True)
        self.base_sustain.lineEdit().setReadOnly(True)
        self.base_sustain.lineEdit().setAlignment(Qt.AlignCenter)
        global_midi_layout.addWidget(self.base_sustain, row, 2, 1, 3)
        row += 1

        # Create offshoot windows for KeySplit and TripleSplit
        # These will be shown/hidden based on split status
        self.keysplit_offshoot = QGroupBox(tr("MIDIswitchSettingsConfigurator", "KeySplit Settings"))
        self.keysplit_offshoot.setMaximumWidth(300)
        keysplit_layout = QGridLayout()
        keysplit_layout.setVerticalSpacing(10)
        keysplit_layout.setHorizontalSpacing(10)
        self.keysplit_offshoot.setLayout(keysplit_layout)

        ks_row = 0
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), ks_row, 0)
        self.key_split_channel = ArrowComboBox()
        self.key_split_channel.setMinimumWidth(80)
        self.key_split_channel.setMaximumWidth(120)
        self.key_split_channel.setMinimumHeight(25)
        self.key_split_channel.setMaximumHeight(25)
        for i in range(16):
            self.key_split_channel.addItem(f"{i + 1}", i)
        self.key_split_channel.setEditable(True)
        self.key_split_channel.lineEdit().setReadOnly(True)
        self.key_split_channel.lineEdit().setAlignment(Qt.AlignCenter)
        keysplit_layout.addWidget(self.key_split_channel, ks_row, 1)
        ks_row += 1

        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), ks_row, 0)
        self.transpose_number2 = ArrowComboBox()
        self.transpose_number2.setMinimumWidth(80)
        self.transpose_number2.setMaximumWidth(120)
        self.transpose_number2.setMinimumHeight(25)
        self.transpose_number2.setMaximumHeight(25)
        for i in range(-64, 65):
            self.transpose_number2.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.transpose_number2.setCurrentIndex(64)
        self.transpose_number2.setEditable(True)
        self.transpose_number2.lineEdit().setReadOnly(True)
        self.transpose_number2.lineEdit().setAlignment(Qt.AlignCenter)
        keysplit_layout.addWidget(self.transpose_number2, ks_row, 1)
        ks_row += 1

        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Curve:")), ks_row, 0)
        self.velocity_curve2 = ArrowComboBox()
        self.velocity_curve2.setMinimumWidth(80)
        self.velocity_curve2.setMaximumWidth(120)
        self.velocity_curve2.setMinimumHeight(25)
        self.velocity_curve2.setMaximumHeight(25)
        # Factory curves (0-6)
        self.velocity_curve2.addItem("Linear", 0)
        self.velocity_curve2.addItem("Aggro", 1)
        self.velocity_curve2.addItem("Slow", 2)
        self.velocity_curve2.addItem("Smooth", 3)
        self.velocity_curve2.addItem("Steep", 4)
        self.velocity_curve2.addItem("Instant", 5)
        self.velocity_curve2.addItem("Turbo", 6)
        # User curves (7-16)
        for i in range(10):
            self.velocity_curve2.addItem(f"User {i+1}", 7 + i)
        self.velocity_curve2.setCurrentIndex(0)
        self.velocity_curve2.setEditable(True)
        self.velocity_curve2.lineEdit().setReadOnly(True)
        self.velocity_curve2.lineEdit().setAlignment(Qt.AlignCenter)
        keysplit_layout.addWidget(self.velocity_curve2, ks_row, 1)
        ks_row += 1

        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Min:")), ks_row, 0)
        self.velocity_min2 = QSlider(Qt.Horizontal)
        self.velocity_min2.setMinimum(1)
        self.velocity_min2.setMaximum(127)
        self.velocity_min2.setValue(1)
        keysplit_layout.addWidget(self.velocity_min2, ks_row, 1)
        self.velocity_min2_value = QLabel("1")
        self.velocity_min2_value.setMinimumWidth(30)
        self.velocity_min2_value.setAlignment(Qt.AlignCenter)
        keysplit_layout.addWidget(self.velocity_min2_value, ks_row, 2)
        self.velocity_min2.valueChanged.connect(lambda v: self.velocity_min2_value.setText(str(v)))
        ks_row += 1

        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Max:")), ks_row, 0)
        self.velocity_max2 = QSlider(Qt.Horizontal)
        self.velocity_max2.setMinimum(1)
        self.velocity_max2.setMaximum(127)
        self.velocity_max2.setValue(127)
        keysplit_layout.addWidget(self.velocity_max2, ks_row, 1)
        self.velocity_max2_value = QLabel("127")
        self.velocity_max2_value.setMinimumWidth(30)
        self.velocity_max2_value.setAlignment(Qt.AlignCenter)
        keysplit_layout.addWidget(self.velocity_max2_value, ks_row, 2)
        self.velocity_max2.valueChanged.connect(lambda v: self.velocity_max2_value.setText(str(v)))
        ks_row += 1

        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sustain:")), ks_row, 0)
        self.keysplit_sustain = ArrowComboBox()
        self.keysplit_sustain.setMinimumWidth(80)
        self.keysplit_sustain.setMaximumWidth(120)
        self.keysplit_sustain.setMinimumHeight(25)
        self.keysplit_sustain.setMaximumHeight(25)
        self.keysplit_sustain.addItem("Ignore", 0)
        self.keysplit_sustain.addItem("Allow", 1)
        self.keysplit_sustain.setCurrentIndex(0)
        self.keysplit_sustain.setEditable(True)
        self.keysplit_sustain.lineEdit().setReadOnly(True)
        self.keysplit_sustain.lineEdit().setAlignment(Qt.AlignCenter)
        keysplit_layout.addWidget(self.keysplit_sustain, ks_row, 1)

        # Connect KeySplit parameter changes to auto-enable keysplit mode
        self.key_split_channel.currentIndexChanged.connect(self._on_keysplit_param_changed)
        self.transpose_number2.currentIndexChanged.connect(self._on_keysplit_param_changed)
        self.velocity_curve2.currentIndexChanged.connect(self._on_keysplit_param_changed)
        self.velocity_min2.valueChanged.connect(self._on_keysplit_param_changed)
        self.velocity_max2.valueChanged.connect(self._on_keysplit_param_changed)
        self.keysplit_sustain.currentIndexChanged.connect(self._on_keysplit_param_changed)

        # TripleSplit offshoot
        self.triplesplit_offshoot = QGroupBox(tr("MIDIswitchSettingsConfigurator", "TripleSplit Settings"))
        self.triplesplit_offshoot.setMaximumWidth(300)
        triplesplit_layout = QGridLayout()
        triplesplit_layout.setVerticalSpacing(10)
        triplesplit_layout.setHorizontalSpacing(10)
        self.triplesplit_offshoot.setLayout(triplesplit_layout)

        ts_row = 0
        triplesplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), ts_row, 0)
        self.key_split2_channel = ArrowComboBox()
        self.key_split2_channel.setMinimumWidth(80)
        self.key_split2_channel.setMaximumWidth(120)
        self.key_split2_channel.setMinimumHeight(25)
        self.key_split2_channel.setMaximumHeight(25)
        for i in range(16):
            self.key_split2_channel.addItem(f"{i + 1}", i)
        self.key_split2_channel.setEditable(True)
        self.key_split2_channel.lineEdit().setReadOnly(True)
        self.key_split2_channel.lineEdit().setAlignment(Qt.AlignCenter)
        triplesplit_layout.addWidget(self.key_split2_channel, ts_row, 1)
        ts_row += 1

        triplesplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), ts_row, 0)
        self.transpose_number3 = ArrowComboBox()
        self.transpose_number3.setMinimumWidth(80)
        self.transpose_number3.setMaximumWidth(120)
        self.transpose_number3.setMinimumHeight(25)
        self.transpose_number3.setMaximumHeight(25)
        for i in range(-64, 65):
            self.transpose_number3.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.transpose_number3.setCurrentIndex(64)
        self.transpose_number3.setEditable(True)
        self.transpose_number3.lineEdit().setReadOnly(True)
        self.transpose_number3.lineEdit().setAlignment(Qt.AlignCenter)
        triplesplit_layout.addWidget(self.transpose_number3, ts_row, 1)
        ts_row += 1

        triplesplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Curve:")), ts_row, 0)
        self.velocity_curve3 = ArrowComboBox()
        self.velocity_curve3.setMinimumWidth(80)
        self.velocity_curve3.setMaximumWidth(120)
        self.velocity_curve3.setMinimumHeight(25)
        self.velocity_curve3.setMaximumHeight(25)
        # Factory curves (0-6)
        self.velocity_curve3.addItem("Linear", 0)
        self.velocity_curve3.addItem("Aggro", 1)
        self.velocity_curve3.addItem("Slow", 2)
        self.velocity_curve3.addItem("Smooth", 3)
        self.velocity_curve3.addItem("Steep", 4)
        self.velocity_curve3.addItem("Instant", 5)
        self.velocity_curve3.addItem("Turbo", 6)
        # User curves (7-16)
        for i in range(10):
            self.velocity_curve3.addItem(f"User {i+1}", 7 + i)
        self.velocity_curve3.setCurrentIndex(0)
        self.velocity_curve3.setEditable(True)
        self.velocity_curve3.lineEdit().setReadOnly(True)
        self.velocity_curve3.lineEdit().setAlignment(Qt.AlignCenter)
        triplesplit_layout.addWidget(self.velocity_curve3, ts_row, 1)
        ts_row += 1

        triplesplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Min:")), ts_row, 0)
        self.velocity_min3 = QSlider(Qt.Horizontal)
        self.velocity_min3.setMinimum(1)
        self.velocity_min3.setMaximum(127)
        self.velocity_min3.setValue(1)
        triplesplit_layout.addWidget(self.velocity_min3, ts_row, 1)
        self.velocity_min3_value = QLabel("1")
        self.velocity_min3_value.setMinimumWidth(30)
        self.velocity_min3_value.setAlignment(Qt.AlignCenter)
        triplesplit_layout.addWidget(self.velocity_min3_value, ts_row, 2)
        self.velocity_min3.valueChanged.connect(lambda v: self.velocity_min3_value.setText(str(v)))
        ts_row += 1

        triplesplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Max:")), ts_row, 0)
        self.velocity_max3 = QSlider(Qt.Horizontal)
        self.velocity_max3.setMinimum(1)
        self.velocity_max3.setMaximum(127)
        self.velocity_max3.setValue(127)
        triplesplit_layout.addWidget(self.velocity_max3, ts_row, 1)
        self.velocity_max3_value = QLabel("127")
        self.velocity_max3_value.setMinimumWidth(30)
        self.velocity_max3_value.setAlignment(Qt.AlignCenter)
        triplesplit_layout.addWidget(self.velocity_max3_value, ts_row, 2)
        self.velocity_max3.valueChanged.connect(lambda v: self.velocity_max3_value.setText(str(v)))
        ts_row += 1

        triplesplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sustain:")), ts_row, 0)
        self.triplesplit_sustain = ArrowComboBox()
        self.triplesplit_sustain.setMinimumWidth(80)
        self.triplesplit_sustain.setMaximumWidth(120)
        self.triplesplit_sustain.setMinimumHeight(25)
        self.triplesplit_sustain.setMaximumHeight(25)
        self.triplesplit_sustain.addItem("Ignore", 0)
        self.triplesplit_sustain.addItem("Allow", 1)
        self.triplesplit_sustain.setCurrentIndex(0)
        self.triplesplit_sustain.setEditable(True)
        self.triplesplit_sustain.lineEdit().setReadOnly(True)
        self.triplesplit_sustain.lineEdit().setAlignment(Qt.AlignCenter)
        triplesplit_layout.addWidget(self.triplesplit_sustain, ts_row, 1)

        # Connect TripleSplit parameter changes to auto-enable triplesplit mode
        self.key_split2_channel.currentIndexChanged.connect(self._on_triplesplit_param_changed)
        self.transpose_number3.currentIndexChanged.connect(self._on_triplesplit_param_changed)
        self.velocity_curve3.currentIndexChanged.connect(self._on_triplesplit_param_changed)
        self.velocity_min3.valueChanged.connect(self._on_triplesplit_param_changed)
        self.velocity_max3.valueChanged.connect(self._on_triplesplit_param_changed)
        self.triplesplit_sustain.currentIndexChanged.connect(self._on_triplesplit_param_changed)

        # Add global MIDI group to main layout
        main_layout.addWidget(global_midi_group)

        # Loop Settings Group
        loop_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "Loop Settings"))
        loop_layout = QGridLayout()
        loop_group.setLayout(loop_layout)
        loop_layout.setHorizontalSpacing(25)
        loop_layout.setColumnStretch(0, 1)     # Left spacer
        loop_layout.setColumnStretch(2, 0)
        loop_layout.setColumnStretch(4, 0)
        loop_layout.setColumnStretch(5, 1)     # Right spacer - pushes everything toward center
        main_layout.addWidget(loop_group)

        # Sync Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sync Mode:")), 0, 1)
        self.unsynced_mode = ArrowComboBox()
        self.unsynced_mode.setMinimumWidth(120)
        self.unsynced_mode.setMinimumHeight(25)
        self.unsynced_mode.setMaximumHeight(25)
        self.unsynced_mode.setEditable(True)
        self.unsynced_mode.lineEdit().setReadOnly(True)
        self.unsynced_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.unsynced_mode.addItem("Loop (Note Prime On)", 0)
        self.unsynced_mode.addItem("Loop (Note Prime Off)", 4)
        self.unsynced_mode.addItem("Sync Mode (Note Prime On)", 2)
        self.unsynced_mode.addItem("Sync Mode (Note Prime Off)", 5)
        self.unsynced_mode.addItem("BPM Bar", 1)
        self.unsynced_mode.addItem("BPM Beat", 3)
        loop_layout.addWidget(self.unsynced_mode, 0, 2)

        # Sample Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sample Mode:")), 0, 3)
        self.sample_mode = ArrowComboBox()
        self.sample_mode.setMinimumWidth(120)
        self.sample_mode.setMinimumHeight(25)
        self.sample_mode.setMaximumHeight(25)
        self.sample_mode.setEditable(True)
        self.sample_mode.lineEdit().setReadOnly(True)
        self.sample_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.sample_mode.addItem("Off", False)
        self.sample_mode.addItem("On", True)
        loop_layout.addWidget(self.sample_mode, 0, 4)

        # Loop Messaging
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Thruloop:")), 1, 1)
        self.loop_messaging_enabled = ArrowComboBox()
        self.loop_messaging_enabled.setMinimumWidth(120)
        self.loop_messaging_enabled.setMinimumHeight(25)
        self.loop_messaging_enabled.setMaximumHeight(25)
        self.loop_messaging_enabled.setEditable(True)
        self.loop_messaging_enabled.lineEdit().setReadOnly(True)
        self.loop_messaging_enabled.lineEdit().setAlignment(Qt.AlignCenter)
        self.loop_messaging_enabled.addItem("Off", False)
        self.loop_messaging_enabled.addItem("On", True)
        loop_layout.addWidget(self.loop_messaging_enabled, 1, 2)

        # Messaging Channel
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Thruloop Channel:")), 1, 3)
        self.loop_messaging_channel = ArrowComboBox()
        self.loop_messaging_channel.setMinimumWidth(120)
        self.loop_messaging_channel.setMinimumHeight(25)
        self.loop_messaging_channel.setMaximumHeight(25)
        self.loop_messaging_channel.setEditable(True)
        self.loop_messaging_channel.lineEdit().setReadOnly(True)
        self.loop_messaging_channel.lineEdit().setAlignment(Qt.AlignCenter)
        for i in range(1, 17):
            self.loop_messaging_channel.addItem(str(i), i)
        self.loop_messaging_channel.setCurrentIndex(15)
        loop_layout.addWidget(self.loop_messaging_channel, 1, 4)

        # Sync MIDI Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "ThruLoop Restart Messaging:")), 2, 1)
        self.sync_midi_mode = ArrowComboBox()
        self.sync_midi_mode.setMinimumWidth(120)
        self.sync_midi_mode.setMinimumHeight(25)
        self.sync_midi_mode.setMaximumHeight(25)
        self.sync_midi_mode.setEditable(True)
        self.sync_midi_mode.lineEdit().setReadOnly(True)
        self.sync_midi_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.sync_midi_mode.addItem("Off", False)
        self.sync_midi_mode.addItem("On", True)
        loop_layout.addWidget(self.sync_midi_mode, 2, 2)

        # Restart Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Thruloop Restart Mode:")), 2, 3)
        self.alternate_restart_mode = ArrowComboBox()
        self.alternate_restart_mode.setMinimumWidth(120)
        self.alternate_restart_mode.setMinimumHeight(25)
        self.alternate_restart_mode.setMaximumHeight(25)
        self.alternate_restart_mode.setEditable(True)
        self.alternate_restart_mode.lineEdit().setReadOnly(True)
        self.alternate_restart_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.alternate_restart_mode.addItem("Restart CC", False)
        self.alternate_restart_mode.addItem("Stop+Start", True)
        loop_layout.addWidget(self.alternate_restart_mode, 2, 4)

        # SmartChord Lights
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Overdub Mode:")), 3, 1)
        self.smart_chord_light = ArrowComboBox()
        self.smart_chord_light.setMinimumWidth(120)
        self.smart_chord_light.setMinimumHeight(25)
        self.smart_chord_light.setMaximumHeight(25)
        self.smart_chord_light.setEditable(True)
        self.smart_chord_light.lineEdit().setReadOnly(True)
        self.smart_chord_light.lineEdit().setAlignment(Qt.AlignCenter)
        self.smart_chord_light.addItem("Default", 0)
        self.smart_chord_light.addItem("8 Track Looper", 1)
        loop_layout.addWidget(self.smart_chord_light, 3, 2)

        # Advanced Settings Group
        advanced_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "Advanced Settings"))
        advanced_layout = QGridLayout()
        advanced_layout.setHorizontalSpacing(25)
        advanced_layout.setColumnStretch(0, 1)    # Left spacer
        advanced_layout.setColumnStretch(2, 0)
        advanced_layout.setColumnStretch(4, 0)
        advanced_layout.setColumnStretch(5, 1)    # Right spacer - pushes everything toward center
        advanced_group.setLayout(advanced_layout)
        main_layout.addWidget(advanced_group)

        # Velocity Interval
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Interval:")), 0, 1)
        self.velocity_sensitivity = ArrowComboBox()
        self.velocity_sensitivity.setMinimumWidth(120)
        self.velocity_sensitivity.setMinimumHeight(25)
        self.velocity_sensitivity.setMaximumHeight(25)
        self.velocity_sensitivity.setEditable(True)
        self.velocity_sensitivity.lineEdit().setReadOnly(True)
        self.velocity_sensitivity.lineEdit().setAlignment(Qt.AlignCenter)
        for i in range(1, 11):
            self.velocity_sensitivity.addItem(str(i), i)
        advanced_layout.addWidget(self.velocity_sensitivity, 0, 2)

        # CC Interval
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "CC Interval:")), 0, 3)
        self.cc_sensitivity = ArrowComboBox()
        self.cc_sensitivity.setMinimumWidth(120)
        self.cc_sensitivity.setMinimumHeight(25)
        self.cc_sensitivity.setMaximumHeight(25)
        self.cc_sensitivity.setEditable(True)
        self.cc_sensitivity.lineEdit().setReadOnly(True)
        self.cc_sensitivity.lineEdit().setAlignment(Qt.AlignCenter)
        for i in range(1, 17):
            self.cc_sensitivity.addItem(str(i), i)
        advanced_layout.addWidget(self.cc_sensitivity, 0, 4)

        # Dynamic Range
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Dynamic Range:")), 1, 1)
        self.random_velocity_modifier = ArrowComboBox()
        self.random_velocity_modifier.setMinimumWidth(120)
        self.random_velocity_modifier.setMinimumHeight(25)
        self.random_velocity_modifier.setMaximumHeight(25)
        self.random_velocity_modifier.setEditable(True)
        self.random_velocity_modifier.lineEdit().setReadOnly(True)
        self.random_velocity_modifier.lineEdit().setAlignment(Qt.AlignCenter)
        for i in range(128):
            self.random_velocity_modifier.addItem(str(i), i)
        advanced_layout.addWidget(self.random_velocity_modifier, 1, 2)

        # OLED Keyboard
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "OLED Keyboard:")), 1, 3)
        self.oled_keyboard = ArrowComboBox()
        self.oled_keyboard.setMinimumWidth(120)
        self.oled_keyboard.setMinimumHeight(25)
        self.oled_keyboard.setMaximumHeight(25)
        self.oled_keyboard.setEditable(True)
        self.oled_keyboard.lineEdit().setReadOnly(True)
        self.oled_keyboard.lineEdit().setAlignment(Qt.AlignCenter)
        self.oled_keyboard.addItem("Style 1", 0)
        self.oled_keyboard.addItem("Style 2", 12)
        advanced_layout.addWidget(self.oled_keyboard, 1, 4)

        # SC Light Mode
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Guide Lights:")), 2, 1)
        self.smart_chord_light_mode = ArrowComboBox()
        self.smart_chord_light_mode.setMinimumWidth(120)
        self.smart_chord_light_mode.setMinimumHeight(25)
        self.smart_chord_light_mode.setMaximumHeight(25)
        self.smart_chord_light_mode.setEditable(True)
        self.smart_chord_light_mode.lineEdit().setReadOnly(True)
        self.smart_chord_light_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.smart_chord_light_mode.addItem("All Off", 1)
        self.smart_chord_light_mode.addItem("SmartChord Off", 2)
        self.smart_chord_light_mode.addItem("All On: Dynamic", 0)
        self.smart_chord_light_mode.addItem("All on: Guitar EADGB", 3)
        self.smart_chord_light_mode.addItem("All on: Guitar ADGBE", 4)
        advanced_layout.addWidget(self.smart_chord_light_mode, 2, 2)

        # Colorblind Mode
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Colorblind Mode:")), 2, 3)
        self.colorblind_mode = ArrowComboBox()
        self.colorblind_mode.setMinimumWidth(120)
        self.colorblind_mode.setMinimumHeight(25)
        self.colorblind_mode.setMaximumHeight(25)
        self.colorblind_mode.setEditable(True)
        self.colorblind_mode.lineEdit().setReadOnly(True)
        self.colorblind_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.colorblind_mode.addItem("Off", 0)
        self.colorblind_mode.addItem("On", 1)
        advanced_layout.addWidget(self.colorblind_mode, 2, 4)

        # RGB Layer Mode
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "RGB Layer Mode:")), 3, 1)
        self.custom_layer_animations = ArrowComboBox()
        self.custom_layer_animations.setMinimumWidth(120)
        self.custom_layer_animations.setMinimumHeight(25)
        self.custom_layer_animations.setMaximumHeight(25)
        self.custom_layer_animations.setEditable(True)
        self.custom_layer_animations.lineEdit().setReadOnly(True)
        self.custom_layer_animations.lineEdit().setAlignment(Qt.AlignCenter)
        self.custom_layer_animations.addItem("Off", False)
        self.custom_layer_animations.addItem("On", True)
        advanced_layout.addWidget(self.custom_layer_animations, 3, 2)

        # CC Loop Recording
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "CC Loop Recording:")), 3, 3)
        self.cc_loop_recording = ArrowComboBox()
        self.cc_loop_recording.setMinimumWidth(120)
        self.cc_loop_recording.setMinimumHeight(25)
        self.cc_loop_recording.setMaximumHeight(25)
        self.cc_loop_recording.setEditable(True)
        self.cc_loop_recording.lineEdit().setReadOnly(True)
        self.cc_loop_recording.lineEdit().setAlignment(Qt.AlignCenter)
        self.cc_loop_recording.addItem("Off", False)
        self.cc_loop_recording.addItem("On", True)
        advanced_layout.addWidget(self.cc_loop_recording, 3, 4)

        # True Sustain
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "True Sustain:")), 4, 1)
        self.true_sustain = ArrowComboBox()
        self.true_sustain.setMinimumWidth(120)
        self.true_sustain.setMinimumHeight(25)
        self.true_sustain.setMaximumHeight(25)
        self.true_sustain.setEditable(True)
        self.true_sustain.lineEdit().setReadOnly(True)
        self.true_sustain.lineEdit().setAlignment(Qt.AlignCenter)
        self.true_sustain.addItem("Off", False)
        self.true_sustain.addItem("On", True)
        advanced_layout.addWidget(self.true_sustain, 4, 2)

        # Aftertouch - REDUCED WIDTH
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Aftertouch:")), 4, 3)
        self.global_aftertouch = ArrowComboBox()
        self.global_aftertouch.setMinimumWidth(80)  # REDUCED from 120
        self.global_aftertouch.setMaximumWidth(120)  # Added max width
        self.global_aftertouch.setMinimumHeight(25)
        self.global_aftertouch.setMaximumHeight(25)
        self.global_aftertouch.addItem("Off", 0)
        self.global_aftertouch.addItem("Reverse", 1)
        self.global_aftertouch.addItem("Bottom-Out", 2)
        self.global_aftertouch.addItem("Post-Actuation", 3)
        self.global_aftertouch.addItem("Vibrato", 4)
        self.global_aftertouch.setCurrentIndex(0)  # Default: Off
        self.global_aftertouch.setEditable(True)
        self.global_aftertouch.lineEdit().setReadOnly(True)
        self.global_aftertouch.lineEdit().setAlignment(Qt.AlignCenter)
        advanced_layout.addWidget(self.global_aftertouch, 4, 4)

        # Aftertouch CC - SAME WIDTH AS CC INTERVAL
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Aftertouch CC:")), 5, 1)
        self.global_aftertouch_cc = ArrowComboBox()
        self.global_aftertouch_cc.setMinimumWidth(80)  # REDUCED from 120
        self.global_aftertouch_cc.setMaximumWidth(120)  # Added max width
        self.global_aftertouch_cc.setMinimumHeight(25)
        self.global_aftertouch_cc.setMaximumHeight(25)
        self.global_aftertouch_cc.addItem("Off", 255)  # 255 = no CC sent, only poly aftertouch
        for cc in range(128):
            self.global_aftertouch_cc.addItem(f"CC#{cc}", cc)
        self.global_aftertouch_cc.setCurrentIndex(0)  # Default: Off
        self.global_aftertouch_cc.setEditable(True)
        self.global_aftertouch_cc.lineEdit().setReadOnly(True)
        self.global_aftertouch_cc.lineEdit().setAlignment(Qt.AlignCenter)
        advanced_layout.addWidget(self.global_aftertouch_cc, 5, 2)

        # KeySplit Modes Group
        keysplit_modes_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "KeySplit Modes"))
        keysplit_modes_layout = QGridLayout()
        keysplit_modes_layout.setHorizontalSpacing(25)
        keysplit_modes_layout.setColumnStretch(0, 1)    # Left spacer
        keysplit_modes_layout.setColumnStretch(2, 0)
        keysplit_modes_layout.setColumnStretch(4, 0)
        keysplit_modes_layout.setColumnStretch(6, 0)
        keysplit_modes_layout.setColumnStretch(7, 1)    # Right spacer - centers content
        keysplit_modes_group.setLayout(keysplit_modes_layout)
        main_layout.addWidget(keysplit_modes_group)

        # Channel Mode
        keysplit_modes_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), 0, 1)
        self.key_split_status = ArrowComboBox()
        self.key_split_status.setMinimumWidth(120)
        self.key_split_status.setMinimumHeight(25)
        self.key_split_status.setMaximumHeight(25)
        self.key_split_status.setEditable(True)
        self.key_split_status.lineEdit().setReadOnly(True)
        self.key_split_status.lineEdit().setAlignment(Qt.AlignCenter)
        self.key_split_status.addItem("Disable Keysplit", 0)
        self.key_split_status.addItem("KeySplit On", 1)
        self.key_split_status.addItem("TripleSplit On", 2)
        self.key_split_status.addItem("Both Splits On", 3)
        self.key_split_status.currentIndexChanged.connect(self.on_channel_split_mode_changed)
        keysplit_modes_layout.addWidget(self.key_split_status, 0, 2)

        # Transpose Mode
        keysplit_modes_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), 0, 3)
        self.key_split_transpose_status = ArrowComboBox()
        self.key_split_transpose_status.setMinimumWidth(120)
        self.key_split_transpose_status.setMinimumHeight(25)
        self.key_split_transpose_status.setMaximumHeight(25)
        self.key_split_transpose_status.setEditable(True)
        self.key_split_transpose_status.lineEdit().setReadOnly(True)
        self.key_split_transpose_status.lineEdit().setAlignment(Qt.AlignCenter)
        self.key_split_transpose_status.addItem("Disable Keysplit", 0)
        self.key_split_transpose_status.addItem("KeySplit On", 1)
        self.key_split_transpose_status.addItem("TripleSplit On", 2)
        self.key_split_transpose_status.addItem("Both Splits On", 3)
        self.key_split_transpose_status.currentIndexChanged.connect(self.on_transpose_split_mode_changed)
        keysplit_modes_layout.addWidget(self.key_split_transpose_status, 0, 4)

        # Velocity Mode
        keysplit_modes_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity:")), 0, 5)
        self.key_split_velocity_status = ArrowComboBox()
        self.key_split_velocity_status.setMinimumWidth(120)
        self.key_split_velocity_status.setMinimumHeight(25)
        self.key_split_velocity_status.setMaximumHeight(25)
        self.key_split_velocity_status.setEditable(True)
        self.key_split_velocity_status.lineEdit().setReadOnly(True)
        self.key_split_velocity_status.lineEdit().setAlignment(Qt.AlignCenter)
        self.key_split_velocity_status.addItem("Disable Keysplit", 0)
        self.key_split_velocity_status.addItem("KeySplit On", 1)
        self.key_split_velocity_status.addItem("TripleSplit On", 2)
        self.key_split_velocity_status.addItem("Both Splits On", 3)
        self.key_split_velocity_status.currentIndexChanged.connect(self.on_velocity_split_mode_changed)
        keysplit_modes_layout.addWidget(self.key_split_velocity_status, 0, 6)

        # Split Settings - Always visible at bottom
        splits_container = QHBoxLayout()
        splits_container.addStretch()
        splits_container.addWidget(self.keysplit_offshoot)
        splits_container.addWidget(self.triplesplit_offshoot)
        splits_container.addStretch()
        main_layout.addLayout(splits_container)

        # Buttons
        self.addStretch()
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        # Default buttons
        save_default_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Save as Default"))
        save_default_btn.setMinimumHeight(30)
        save_default_btn.setMaximumHeight(30)
        save_default_btn.setStyleSheet("QPushButton { border-radius: 5px; }")
        save_default_btn.clicked.connect(lambda: self.on_save_slot(0))
        buttons_layout.addWidget(save_default_btn)

        load_default_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Load Default"))
        load_default_btn.setMinimumHeight(30)
        load_default_btn.setMaximumHeight(30)
        load_default_btn.setStyleSheet("QPushButton { border-radius: 5px; }")
        load_default_btn.clicked.connect(lambda: self.on_load_slot(0))
        buttons_layout.addWidget(load_default_btn)

        load_current_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Load Current Settings"))
        load_current_btn.setMinimumHeight(30)
        load_current_btn.setMaximumHeight(30)
        load_current_btn.setStyleSheet("QPushButton { border-radius: 5px; }")
        load_current_btn.clicked.connect(self.on_load_current_settings)
        buttons_layout.addWidget(load_current_btn)

        reset_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Reset to Defaults"))
        reset_btn.setMinimumHeight(30)
        reset_btn.setMaximumHeight(30)
        reset_btn.setStyleSheet("QPushButton { border-radius: 5px; }")
        reset_btn.clicked.connect(self.on_reset)
        buttons_layout.addWidget(reset_btn)

        self.addLayout(buttons_layout)

        # Save slot buttons
        save_slots_layout = QHBoxLayout()
        save_slots_layout.addStretch()
        for i in range(1, 5):
            btn = QPushButton(tr("MIDIswitchSettingsConfigurator", f"Save to Slot {i}"))
            btn.setMinimumHeight(30)
            btn.setMaximumHeight(30)
            btn.setStyleSheet("QPushButton { border-radius: 5px; }")
            btn.clicked.connect(lambda checked, slot=i: self.on_save_slot(slot))
            save_slots_layout.addWidget(btn)
        self.addLayout(save_slots_layout)

        # Load slot buttons
        load_slots_layout = QHBoxLayout()
        load_slots_layout.addStretch()
        for i in range(1, 5):
            btn = QPushButton(tr("MIDIswitchSettingsConfigurator", f"Load Slot {i}"))
            btn.setMinimumHeight(30)
            btn.setMaximumHeight(30)
            btn.setStyleSheet("QPushButton { border-radius: 5px; }")
            btn.clicked.connect(lambda checked, slot=i: self.on_load_slot(slot))
            load_slots_layout.addWidget(btn)
        self.addLayout(load_slots_layout)

        # Apply stylesheet to center combo box text
        main_widget.setStyleSheet("""
            QComboBox {
                text-align: center;
            }
        """)

        # Connect widgets to real-time HID updates
        self.global_channel.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_CHANNEL_NUMBER, self.global_channel.currentData())
        )
        self.global_transpose.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_TRANSPOSE_NUMBER, self.global_transpose.currentData())
        )
        self.global_velocity_curve.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_HE_VELOCITY_CURVE, self.global_velocity_curve.currentData())
        )
        self.global_velocity_min.valueChanged.connect(
            lambda v: [self.velocity_min_value_label.setText(str(v)),
                      self.send_param_update(PARAM_HE_VELOCITY_MIN, v)]
        )
        self.global_velocity_max.valueChanged.connect(
            lambda v: [self.velocity_max_value_label.setText(str(v)),
                      self.send_param_update(PARAM_HE_VELOCITY_MAX, v)]
        )
        self.base_sustain.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_BASE_SUSTAIN, self.base_sustain.currentData())
        )
        self.global_aftertouch.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_AFTERTOUCH_MODE, self.global_aftertouch.currentData())
        )
        self.global_aftertouch_cc.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_AFTERTOUCH_CC, self.global_aftertouch_cc.currentData())
        )

        # KeySplit widgets
        self.key_split_channel.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_KEYSPLITCHANNEL, self.key_split_channel.currentData())
        )
        self.transpose_number2.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_TRANSPOSE_NUMBER2, self.transpose_number2.currentData())
        )
        self.velocity_curve2.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_KEYSPLIT_HE_VELOCITY_CURVE, self.velocity_curve2.currentData())
        )
        self.velocity_min2.valueChanged.connect(
            lambda v: [self.velocity_min2_value.setText(str(v)),
                      self.send_param_update(PARAM_KEYSPLIT_HE_VELOCITY_MIN, v)]
        )
        self.velocity_max2.valueChanged.connect(
            lambda v: [self.velocity_max2_value.setText(str(v)),
                      self.send_param_update(PARAM_KEYSPLIT_HE_VELOCITY_MAX, v)]
        )
        self.keysplit_sustain.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_KEYSPLIT_SUSTAIN, self.keysplit_sustain.currentData())
        )

        # TripleSplit widgets
        self.key_split2_channel.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_KEYSPLIT2CHANNEL, self.key_split2_channel.currentData())
        )
        self.transpose_number3.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_TRANSPOSE_NUMBER3, self.transpose_number3.currentData())
        )
        self.velocity_curve3.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_TRIPLESPLIT_HE_VELOCITY_CURVE, self.velocity_curve3.currentData())
        )
        self.velocity_min3.valueChanged.connect(
            lambda v: [self.velocity_min3_value.setText(str(v)),
                      self.send_param_update(PARAM_TRIPLESPLIT_HE_VELOCITY_MIN, v)]
        )
        self.velocity_max3.valueChanged.connect(
            lambda v: [self.velocity_max3_value.setText(str(v)),
                      self.send_param_update(PARAM_TRIPLESPLIT_HE_VELOCITY_MAX, v)]
        )
        self.triplesplit_sustain.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_TRIPLESPLIT_SUSTAIN, self.triplesplit_sustain.currentData())
        )

        # Split status - send HID updates for all three status dropdowns
        self.key_split_status.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_KEYSPLITSTATUS, self.key_split_status.currentData())
        )
        self.key_split_transpose_status.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_KEYSPLITTRANSPOSESTATUS, self.key_split_transpose_status.currentData())
        )
        self.key_split_velocity_status.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_KEYSPLITVELOCITYSTATUS, self.key_split_velocity_status.currentData())
        )

        # Set initial offshoot visibility based on default dropdown values (all 0, so both hidden)
        self._update_offshoot_visibility()

    def send_param_update(self, param_id, value):
        """Send real-time HID parameter update to keyboard"""
        try:
            if self.device and isinstance(self.device, VialKeyboard):
                self.device.keyboard.set_keyboard_param_single(param_id, value)
        except Exception as e:
            # Silently fail - firmware may not support this parameter yet
            pass

    def on_channel_split_mode_changed(self):
        """Handle channel split mode changes - show/hide offshoots and update UI"""
        self._update_offshoot_visibility()

    def on_transpose_split_mode_changed(self):
        """Handle transpose split mode changes - show/hide offshoots and update UI"""
        self._update_offshoot_visibility()

    def on_velocity_split_mode_changed(self):
        """Handle velocity split mode changes - show/hide offshoots and update UI"""
        self._update_offshoot_visibility()

    def _update_offshoot_visibility(self):
        """Update offshoot visibility based on any of the three status dropdowns"""
        # Check all three status values
        channel_status = self.key_split_status.currentData()
        transpose_status = self.key_split_transpose_status.currentData()
        velocity_status = self.key_split_velocity_status.currentData()

        # Show KeySplit offshoot if ANY status has keysplit enabled (1 or 3)
        show_keysplit = any(status in [1, 3] for status in [channel_status, transpose_status, velocity_status])

        # Show TripleSplit offshoot if ANY status has triplesplit enabled (2 or 3)
        show_triplesplit = any(status in [2, 3] for status in [channel_status, transpose_status, velocity_status])

        self.keysplit_offshoot.setVisible(show_keysplit)
        self.triplesplit_offshoot.setVisible(show_triplesplit)

    def _on_keysplit_param_changed(self):
        """Auto-enable keysplit when any KeySplit parameter is changed"""
        # Enable keysplit bit in all three status dropdowns (0→1 or 2→3)
        self._enable_keysplit_in_dropdown(self.key_split_status)
        self._enable_keysplit_in_dropdown(self.key_split_transpose_status)
        self._enable_keysplit_in_dropdown(self.key_split_velocity_status)

    def _on_triplesplit_param_changed(self):
        """Auto-enable triplesplit when any TripleSplit parameter is changed"""
        # Enable triplesplit bit in all three status dropdowns (0→2 or 1→3)
        self._enable_triplesplit_in_dropdown(self.key_split_status)
        self._enable_triplesplit_in_dropdown(self.key_split_transpose_status)
        self._enable_triplesplit_in_dropdown(self.key_split_velocity_status)

    def _enable_keysplit_in_dropdown(self, dropdown):
        """Enable keysplit bit in a dropdown (0→1 or 2→3)"""
        current = dropdown.currentData()
        if current == 0:
            # Set to KeySplit On
            for i in range(dropdown.count()):
                if dropdown.itemData(i) == 1:
                    dropdown.setCurrentIndex(i)
                    break
        elif current == 2:
            # Set to Both Splits On
            for i in range(dropdown.count()):
                if dropdown.itemData(i) == 3:
                    dropdown.setCurrentIndex(i)
                    break
        # If already 1 or 3, do nothing

    def _enable_triplesplit_in_dropdown(self, dropdown):
        """Enable triplesplit bit in a dropdown (0→2 or 1→3)"""
        current = dropdown.currentData()
        if current == 0:
            # Set to TripleSplit On
            for i in range(dropdown.count()):
                if dropdown.itemData(i) == 2:
                    dropdown.setCurrentIndex(i)
                    break
        elif current == 1:
            # Set to Both Splits On
            for i in range(dropdown.count()):
                if dropdown.itemData(i) == 3:
                    dropdown.setCurrentIndex(i)
                    break
        # If already 2 or 3, do nothing

    def get_current_settings(self):
        """Get current UI settings as dictionary"""
        return {
            "velocity_sensitivity": self.velocity_sensitivity.currentData(),
            "cc_sensitivity": self.cc_sensitivity.currentData(),
            "transpose_number2": self.transpose_number2.currentData(),
            "transpose_number3": self.transpose_number3.currentData(),
            "random_velocity_modifier": self.random_velocity_modifier.currentData(),
            "oled_keyboard": self.oled_keyboard.currentData(),
            "smart_chord_light": self.smart_chord_light.currentData(),
            "smart_chord_light_mode": self.smart_chord_light_mode.currentData(),
            "key_split_channel": self.key_split_channel.currentData(),
            "key_split2_channel": self.key_split2_channel.currentData(),
            "key_split_status": self.key_split_status.currentData(),
            "key_split_transpose_status": self.key_split_transpose_status.currentData(),
            "key_split_velocity_status": self.key_split_velocity_status.currentData(),
            "custom_layer_animations_enabled": self.custom_layer_animations.currentData(),
            "unsynced_mode_active": self.unsynced_mode.currentData(),
            "sample_mode_active": self.sample_mode.currentData(),
            "loop_messaging_enabled": self.loop_messaging_enabled.currentData(),
            "loop_messaging_channel": self.loop_messaging_channel.currentData(),
            "sync_midi_mode": self.sync_midi_mode.currentData(),
            "alternate_restart_mode": self.alternate_restart_mode.currentData(),
            "colorblindmode": self.colorblind_mode.currentData(),
            "cclooprecording": self.cc_loop_recording.currentData(),
            "truesustain": self.true_sustain.currentData(),
            # KeySplit/TripleSplit velocity settings
            "velocity_curve2": self.velocity_curve2.currentData(),
            "velocity_min2": self.velocity_min2.value(),  # Changed from currentData() to value()
            "velocity_max2": self.velocity_max2.value(),  # Changed from currentData() to value()
            "velocity_curve3": self.velocity_curve3.currentData(),
            "velocity_min3": self.velocity_min3.value(),  # Changed from currentData() to value()
            "velocity_max3": self.velocity_max3.value(),  # Changed from currentData() to value()
            # Global MIDI settings
            "global_transpose": self.global_transpose.currentData(),
            "global_channel": self.global_channel.currentData(),
            "global_velocity_curve": self.global_velocity_curve.currentData(),
            "global_aftertouch": self.global_aftertouch.currentData(),
            "global_velocity_min": self.global_velocity_min.value(),  # Changed from currentData() to value()
            "global_velocity_max": self.global_velocity_max.value(),  # Changed from currentData() to value()
            "global_aftertouch_cc": self.global_aftertouch_cc.currentData(),
            # Sustain settings
            "base_sustain": self.base_sustain.currentData(),
            "keysplit_sustain": self.keysplit_sustain.currentData(),
            "triplesplit_sustain": self.triplesplit_sustain.currentData()
        }
    
    def apply_settings(self, config):
        """Apply settings dictionary to UI"""
        def set_combo_by_data(combo, value, default_value=None):
            for i in range(combo.count()):
                if combo.itemData(i) == value:
                    combo.setCurrentIndex(i)
                    return
            if default_value is not None:
                for i in range(combo.count()):
                    if combo.itemData(i) == default_value:
                        combo.setCurrentIndex(i)
                        return
        
        set_combo_by_data(self.velocity_sensitivity, config.get("velocity_sensitivity"), 1)
        set_combo_by_data(self.cc_sensitivity, config.get("cc_sensitivity"), 1)
        set_combo_by_data(self.transpose_number2, config.get("transpose_number2"), 0)
        set_combo_by_data(self.transpose_number3, config.get("transpose_number3"), 0)
        set_combo_by_data(self.random_velocity_modifier, config.get("random_velocity_modifier"), 0)
        set_combo_by_data(self.oled_keyboard, config.get("oled_keyboard"), 0)
        set_combo_by_data(self.smart_chord_light, config.get("smart_chord_light"), 0)
        set_combo_by_data(self.smart_chord_light_mode, config.get("smart_chord_light_mode"), 0)
        set_combo_by_data(self.key_split_channel, config.get("key_split_channel"), 0)
        set_combo_by_data(self.key_split2_channel, config.get("key_split2_channel"), 0)
        set_combo_by_data(self.key_split_status, config.get("key_split_status"), 0)
        set_combo_by_data(self.key_split_transpose_status, config.get("key_split_transpose_status"), 0)
        set_combo_by_data(self.key_split_velocity_status, config.get("key_split_velocity_status"), 0)
        set_combo_by_data(self.custom_layer_animations, config.get("custom_layer_animations_enabled"), False)
        set_combo_by_data(self.unsynced_mode, config.get("unsynced_mode_active"), False)
        set_combo_by_data(self.sample_mode, config.get("sample_mode_active"), False)
        set_combo_by_data(self.loop_messaging_enabled, config.get("loop_messaging_enabled"), False)
        set_combo_by_data(self.loop_messaging_channel, config.get("loop_messaging_channel"), 16)
        set_combo_by_data(self.sync_midi_mode, config.get("sync_midi_mode"), False)
        set_combo_by_data(self.alternate_restart_mode, config.get("alternate_restart_mode"), False)
        set_combo_by_data(self.colorblind_mode, config.get("colorblindmode"), 0)
        set_combo_by_data(self.cc_loop_recording, config.get("cclooprecording"), False)
        set_combo_by_data(self.true_sustain, config.get("truesustain"), False)
        # KeySplit/TripleSplit velocity settings
        set_combo_by_data(self.velocity_curve2, config.get("velocity_curve2"), 2)
        self.velocity_min2.setValue(config.get("velocity_min2", 1))  # Changed to slider setValue
        self.velocity_max2.setValue(config.get("velocity_max2", 127))  # Changed to slider setValue
        set_combo_by_data(self.velocity_curve3, config.get("velocity_curve3"), 2)
        self.velocity_min3.setValue(config.get("velocity_min3", 1))  # Changed to slider setValue
        self.velocity_max3.setValue(config.get("velocity_max3", 127))  # Changed to slider setValue
        # Global MIDI settings
        set_combo_by_data(self.global_transpose, config.get("global_transpose"), 0)
        set_combo_by_data(self.global_channel, config.get("global_channel"), 0)
        set_combo_by_data(self.global_velocity_curve, config.get("global_velocity_curve"), 2)
        set_combo_by_data(self.global_aftertouch, config.get("global_aftertouch"), 0)
        self.global_velocity_min.setValue(config.get("global_velocity_min", 1))  # Changed to slider setValue
        self.global_velocity_max.setValue(config.get("global_velocity_max", 127))  # Changed to slider setValue
        set_combo_by_data(self.global_aftertouch_cc, config.get("global_aftertouch_cc"), 255)
        # Sustain settings
        set_combo_by_data(self.base_sustain, config.get("base_sustain"), 0)
        set_combo_by_data(self.keysplit_sustain, config.get("keysplit_sustain"), 0)
        set_combo_by_data(self.triplesplit_sustain, config.get("triplesplit_sustain"), 0)
    
    def pack_basic_data(self, settings):
        """Pack basic settings into 17-byte structure"""
        data = bytearray(17)

        struct.pack_into('<I', data, 0, settings["velocity_sensitivity"])
        struct.pack_into('<I', data, 4, settings["cc_sensitivity"])

        offset = 8
        data[offset] = settings["global_channel"]; offset += 1  # global channel
        data[offset] = settings["global_transpose"] & 0xFF; offset += 1  # global transpose
        data[offset] = 0; offset += 1  # octave_number
        data[offset] = settings["transpose_number2"] & 0xFF; offset += 1
        data[offset] = 0; offset += 1  # octave_number2
        data[offset] = settings["transpose_number3"] & 0xFF; offset += 1
        data[offset] = 0; offset += 1  # octave_number3
        data[offset] = settings["random_velocity_modifier"]; offset += 1

        struct.pack_into('<I', data, offset, settings["oled_keyboard"]); offset += 4

        data[offset] = settings["smart_chord_light"]; offset += 1
        data[offset] = settings["smart_chord_light_mode"]; offset += 1

        return data
    
    def pack_advanced_data(self, settings):
        """Pack advanced settings into 29-byte structure (expanded for global velocity settings and sustain)"""
        data = bytearray(29)

        offset = 0
        data[offset] = settings["key_split_channel"]; offset += 1
        data[offset] = settings["key_split2_channel"]; offset += 1
        data[offset] = settings["key_split_status"]; offset += 1
        data[offset] = settings["key_split_transpose_status"]; offset += 1
        data[offset] = settings["key_split_velocity_status"]; offset += 1
        data[offset] = 1 if settings["custom_layer_animations_enabled"] else 0; offset += 1
        data[offset] = settings["unsynced_mode_active"]; offset += 1
        data[offset] = 1 if settings["sample_mode_active"] else 0; offset += 1
        data[offset] = 1 if settings["loop_messaging_enabled"] else 0; offset += 1
        data[offset] = settings["loop_messaging_channel"]; offset += 1
        data[offset] = 1 if settings["sync_midi_mode"] else 0; offset += 1
        data[offset] = 1 if settings["alternate_restart_mode"] else 0; offset += 1
        data[offset] = settings["colorblindmode"]; offset += 1
        data[offset] = 1 if settings["cclooprecording"] else 0; offset += 1
        data[offset] = 1 if settings["truesustain"] else 0; offset += 1
        # KeySplit/TripleSplit velocity settings
        data[offset] = settings["velocity_curve2"]; offset += 1
        data[offset] = settings["velocity_min2"]; offset += 1
        data[offset] = settings["velocity_max2"]; offset += 1
        data[offset] = settings["velocity_curve3"]; offset += 1
        data[offset] = settings["velocity_min3"]; offset += 1
        data[offset] = settings["velocity_max3"]; offset += 1
        # Global MIDI velocity and aftertouch settings
        data[offset] = settings["global_velocity_curve"]; offset += 1
        data[offset] = settings["global_velocity_min"]; offset += 1
        data[offset] = settings["global_velocity_max"]; offset += 1
        data[offset] = settings["global_aftertouch"]; offset += 1
        data[offset] = settings["global_aftertouch_cc"]; offset += 1
        # Sustain settings (bytes 26-28)
        data[offset] = settings["base_sustain"]; offset += 1
        data[offset] = settings["keysplit_sustain"]; offset += 1
        data[offset] = settings["triplesplit_sustain"]; offset += 1

        return data
    
    def on_save_slot(self, slot):
        """Save current settings to slot"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")
            
            settings = self.get_current_settings()
            
            basic_data = self.pack_basic_data(settings)
            if not self.device.keyboard.save_midi_slot(slot, basic_data):
                raise RuntimeError(f"Failed to save to slot {slot}")
            
            QtCore.QTimer.singleShot(50, lambda: self._send_advanced_data(settings))
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save to slot {slot}: {str(e)}")
    
    def _send_advanced_data(self, settings):
        """Send advanced data (helper for save operations)"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                return
                
            advanced_data = self.pack_advanced_data(settings)
            if not self.device.keyboard.set_midi_advanced_config(advanced_data):
                raise RuntimeError("Failed to send advanced config")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to send advanced data: {str(e)}")
    
    def on_load_slot(self, slot):
        """Load settings from slot with multi-packet handling"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")
                
            if not self.device.keyboard.load_midi_slot(slot):
                raise RuntimeError(f"Failed to load from slot {slot}")
                
            # Small delay then get the loaded configuration
            QtCore.QTimer.singleShot(100, lambda: self._load_config_after_slot_load(slot))
                
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to load from slot {slot}: {str(e)}")
    
    def _load_config_after_slot_load(self, slot):
        """Get and apply configuration after slot load"""
        try:
            config = self.device.keyboard.get_midi_config()
            
            if not config:
                raise RuntimeError("Failed to get config after slot load")
            
            self.apply_settings(config)
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to apply loaded config: {str(e)}")
    
    def on_load_current_settings(self):
        """Load current settings from keyboard using multi-packet collection"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")
            
            config = self.device.keyboard.get_midi_config()
            
            if not config:
                raise RuntimeError("Failed to load current settings")
            
            self.apply_settings(config)
                
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to load current settings: {str(e)}")
    
    def on_reset(self):
        """Reset to default settings"""
        try:
            reply = QMessageBox.question(None, "Confirm Reset", 
                                       "Reset all keyboard settings to defaults? This cannot be undone.",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                if not self.device or not isinstance(self.device, VialKeyboard):
                    raise RuntimeError("Device not connected")
                    
                if not self.device.keyboard.reset_midi_config():
                    raise RuntimeError("Failed to reset settings")
                    
                self.reset_ui_to_defaults()
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to reset settings: {str(e)}")
    
    def reset_ui_to_defaults(self):
        """Reset UI to default values"""
        defaults = {
            "velocity_sensitivity": 1,
            "cc_sensitivity": 1,
            "transpose_number2": 0,
            "transpose_number3": 0,
            "random_velocity_modifier": 127,
            "oled_keyboard": 0,
            "smart_chord_light": 0,
            "smart_chord_light_mode": 0,
            "key_split_channel": 0,
            "key_split2_channel": 0,
            "key_split_status": 0,
            "key_split_transpose_status": 0,
            "key_split_velocity_status": 0,
            "custom_layer_animations_enabled": False,
            "unsynced_mode_active": 0,
            "sample_mode_active": False,
            "loop_messaging_enabled": False,
            "loop_messaging_channel": 16,
            "sync_midi_mode": False,
            "alternate_restart_mode": False,
            "colorblindmode": 0,
            "cclooprecording": False,
            "truesustain": False,
            "velocity_curve2": 2,
            "velocity_min2": 1,
            "velocity_max2": 127,
            "velocity_curve3": 2,
            "velocity_min3": 1,
            "velocity_max3": 127,
            "global_transpose": 0,
            "global_channel": 0,
            "global_velocity_curve": 2,
            "global_aftertouch": 0,
            "global_velocity_min": 1,
            "global_velocity_max": 127,
            "global_aftertouch_cc": 255,  # 255 = off (no CC sent)
            "base_sustain": 0,
            "keysplit_sustain": 0,
            "triplesplit_sustain": 0
        }
        self.apply_settings(defaults)
    
    def valid(self):
        return isinstance(self.device, VialKeyboard)

    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return

        # Load MIDI configuration from keyboard
        if hasattr(self.device.keyboard, 'midi_config') and self.device.keyboard.midi_config:
            self.apply_settings(self.device.keyboard.midi_config)

# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtWidgets import (QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QLabel, 
                           QSizePolicy, QGroupBox, QGridLayout, QSlider, QCheckBox,
                           QMessageBox, QScrollArea, QFrame, QComboBox)
from PyQt5.QtCore import Qt
from PyQt5 import QtCore

from editor.basic_editor import BasicEditor
from util import tr
from vial_device import VialKeyboard

class LayerActuationConfigurator(BasicEditor):
    
    def __init__(self):
        super().__init__()
        
        # Master widgets
        self.master_widgets = {}
        
        # Single layer widgets
        self.layer_widgets = {}
        
        # Current layer being viewed
        self.current_layer = 0
        
        # All layer data stored in memory
        self.layer_data = []
        for _ in range(12):
            self.layer_data.append({
                'normal': 80,
                'midi': 80,
                'aftertouch': 0,
                'velocity': 2,
                'rapid': 4,
                'midi_rapid_sens': 10,
                'midi_rapid_vel': 10,
                'vel_speed': 10,
                'aftertouch_cc': 255,  # 255 = off (no CC sent)
                'rapidfire_enabled': False,
                'midi_rapidfire_enabled': False,
                # HE Velocity defaults
                'use_fixed_velocity': False,
                'he_curve': 2,  # Medium (linear)
                'he_min': 1,
                'he_max': 127
            })
        
        # Flag to prevent recursion
        self.updating_from_master = False
        
        # Per-layer mode
        self.per_layer_enabled = False
        
        # Advanced options shown
        self.advanced_shown = False
        
        self.setup_ui()
        
    def setup_ui(self):
        self.addStretch()
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumSize(900, 600)
        
        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_widget.setLayout(main_layout)
        
        scroll.setWidget(main_widget)
        self.addWidget(scroll)
        self.setAlignment(scroll, QtCore.Qt.AlignHCenter)
        
        # Info label
        info_label = QLabel(tr("LayerActuationConfigurator", 
            "Configure actuation distances and settings per layer"))
        info_label.setStyleSheet("QLabel { color: #666; font-style: italic; font-size: 10px; margin: 5px; }")
        main_layout.addWidget(info_label, alignment=QtCore.Qt.AlignCenter)
        
        # Create master controls group
        self.master_group = self.create_master_group()
        main_layout.addWidget(self.master_group)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # Layer selector container (hidden by default)
        self.layer_selector_container = QWidget()
        layer_selector_layout = QVBoxLayout()
        layer_selector_layout.setSpacing(10)
        self.layer_selector_container.setLayout(layer_selector_layout)
        
        # Layer dropdown
        selector_row = QHBoxLayout()
        selector_row.addStretch()
        selector_label = QLabel(tr("LayerActuationConfigurator", "Select Layer:"))
        selector_label.setStyleSheet("QLabel { font-weight: bold; font-size: 11px; }")
        selector_row.addWidget(selector_label)
        
        self.layer_dropdown = ArrowComboBox()
        self.layer_dropdown.setMinimumWidth(150)
        self.layer_dropdown.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        for i in range(12):
            self.layer_dropdown.addItem(f"Layer {i}", i)
        self.layer_dropdown.setEditable(True)
        self.layer_dropdown.lineEdit().setReadOnly(True)
        self.layer_dropdown.lineEdit().setAlignment(Qt.AlignCenter)
        self.layer_dropdown.currentIndexChanged.connect(self.on_layer_changed)
        selector_row.addWidget(self.layer_dropdown)
        selector_row.addStretch()
        
        layer_selector_layout.addLayout(selector_row)
        
        # Single layer group
        self.layer_group = self.create_layer_group()
        layer_selector_layout.addWidget(self.layer_group, alignment=QtCore.Qt.AlignCenter)
        
        self.layer_selector_container.setVisible(False)
        main_layout.addWidget(self.layer_selector_container)
        
        main_layout.addStretch()
        
        # Buttons
        self.addStretch()
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        # Button style - bigger and less rounded
        button_style = "QPushButton { border-radius: 3px; padding: 8px 16px; }"

        save_btn = QPushButton(tr("LayerActuationConfigurator", "Save to Keyboard"))
        save_btn.setMinimumHeight(45)
        save_btn.setMinimumWidth(180)
        save_btn.setStyleSheet(button_style)
        save_btn.clicked.connect(self.on_save)
        buttons_layout.addWidget(save_btn)

        load_btn = QPushButton(tr("LayerActuationConfigurator", "Load from Keyboard"))
        load_btn.setMinimumHeight(45)
        load_btn.setMinimumWidth(210)
        load_btn.setStyleSheet(button_style)
        load_btn.clicked.connect(self.on_load_from_keyboard)
        buttons_layout.addWidget(load_btn)

        reset_btn = QPushButton(tr("LayerActuationConfigurator", "Reset All to Defaults"))
        reset_btn.setMinimumHeight(45)
        reset_btn.setMinimumWidth(210)
        reset_btn.setStyleSheet(button_style)
        reset_btn.clicked.connect(self.on_reset)
        buttons_layout.addWidget(reset_btn)

        self.addLayout(buttons_layout)
    
    def create_master_group(self):
        """Create the master control group with all settings"""
        group = QGroupBox(tr("LayerActuationConfigurator", "Master Settings (All Layers)"))
        group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; }")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        group.setLayout(layout)
        
        # Top row with both checkboxes
        checkboxes_layout = QHBoxLayout()
        
        # Master per-layer checkbox
        self.per_layer_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Enable Per-Layer Settings"))
        self.per_layer_checkbox.setStyleSheet("QCheckBox { font-weight: bold; font-size: 11px; }")
        self.per_layer_checkbox.stateChanged.connect(self.on_per_layer_toggled)
        checkboxes_layout.addWidget(self.per_layer_checkbox)
        
        checkboxes_layout.addSpacing(20)
        
        # Show Advanced Options checkbox
        self.advanced_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Show Advanced Actuation Options"))
        self.advanced_checkbox.setStyleSheet("QCheckBox { font-size: 11px; }")
        self.advanced_checkbox.stateChanged.connect(self.on_advanced_toggled)
        checkboxes_layout.addWidget(self.advanced_checkbox)
        
        checkboxes_layout.addStretch()
        layout.addLayout(checkboxes_layout)
        
        # Add separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Normal Keys Actuation (slider) - ALWAYS VISIBLE
        slider_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Normal Keys Actuation:"))
        label.setMinimumWidth(200)
        slider_layout.addWidget(label)
        
        normal_slider = QSlider(Qt.Horizontal)
        normal_slider.setMinimum(0)
        normal_slider.setMaximum(100)
        normal_slider.setValue(80)
        slider_layout.addWidget(normal_slider)
        
        normal_value_label = QLabel("2.00mm (80)")
        normal_value_label.setMinimumWidth(100)
        normal_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        slider_layout.addWidget(normal_value_label)
        
        layout.addLayout(slider_layout)
        normal_slider.valueChanged.connect(
            lambda v, lbl=normal_value_label: self.on_master_slider_changed('normal', v, lbl)
        )
        
        # Enable Rapidfire checkbox - ALWAYS VISIBLE
        rapid_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Enable Rapidfire"))
        rapid_checkbox.setChecked(False)
        layout.addWidget(rapid_checkbox)
        rapid_checkbox.stateChanged.connect(self.on_rapidfire_toggled)
        
        # Rapidfire Sensitivity (slider) - hidden by default
        rapid_slider_layout = QHBoxLayout()
        rapid_label = QLabel(tr("LayerActuationConfigurator", "Rapidfire Sensitivity:"))
        rapid_label.setMinimumWidth(200)
        rapid_slider_layout.addWidget(rapid_label)
        
        rapid_slider = QSlider(Qt.Horizontal)
        rapid_slider.setMinimum(1)
        rapid_slider.setMaximum(100)
        rapid_slider.setValue(4)
        rapid_slider_layout.addWidget(rapid_slider)
        
        rapid_value_label = QLabel("4")
        rapid_value_label.setMinimumWidth(100)
        rapid_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        rapid_slider_layout.addWidget(rapid_value_label)
        
        rapid_slider_widget = QWidget()
        rapid_slider_widget.setLayout(rapid_slider_layout)
        rapid_slider_widget.setVisible(False)
        layout.addWidget(rapid_slider_widget)
        
        rapid_slider.valueChanged.connect(
            lambda v, lbl=rapid_value_label: self.on_master_slider_changed('rapid', v, lbl)
        )
        
        # === ADVANCED OPTIONS (hidden by default) ===
        self.advanced_widget = QWidget()
        advanced_layout_main = QVBoxLayout()
        advanced_layout_main.setSpacing(8)
        advanced_layout_main.setContentsMargins(0, 10, 0, 0)
        self.advanced_widget.setLayout(advanced_layout_main)
        self.advanced_widget.setVisible(False)

        # Add separator
        adv_line = QFrame()
        adv_line.setFrameShape(QFrame.HLine)
        adv_line.setFrameShadow(QFrame.Sunken)
        advanced_layout_main.addWidget(adv_line)

        # Title for MIDI settings section
        midi_settings_title = QLabel(tr("LayerActuationConfigurator", "Basic MIDI Settings"))
        midi_settings_title.setStyleSheet("QLabel { font-weight: bold; font-size: 11px; margin: 5px 0px; }")
        advanced_layout_main.addWidget(midi_settings_title)

        # Container for MIDI settings and split offshoots (side by side)
        content_container = QHBoxLayout()
        advanced_layout = QVBoxLayout()

        # Split Mode control
        split_mode_layout = QHBoxLayout()
        split_mode_label = QLabel(tr("LayerActuationConfigurator", "Split Mode:"))
        split_mode_label.setMinimumWidth(200)
        split_mode_layout.addWidget(split_mode_label)

        self.actuation_split_mode = ArrowComboBox()
        self.actuation_split_mode.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        self.actuation_split_mode.addItem("Disable Keysplit", 0)
        self.actuation_split_mode.addItem("KeySplit On", 1)
        self.actuation_split_mode.addItem("TripleSplit On", 2)
        self.actuation_split_mode.addItem("Both Splits On", 3)
        self.actuation_split_mode.setCurrentIndex(0)
        self.actuation_split_mode.setEditable(True)
        self.actuation_split_mode.lineEdit().setReadOnly(True)
        self.actuation_split_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.actuation_split_mode.currentIndexChanged.connect(self.on_actuation_split_mode_changed)
        split_mode_layout.addWidget(self.actuation_split_mode)
        split_mode_layout.addStretch()

        advanced_layout.addLayout(split_mode_layout)

        # MIDI Keys Actuation (slider)
        midi_slider_layout = QHBoxLayout()
        midi_label = QLabel(tr("LayerActuationConfigurator", "MIDI Keys Actuation:"))
        midi_label.setMinimumWidth(200)
        midi_slider_layout.addWidget(midi_label)
        
        midi_slider = QSlider(Qt.Horizontal)
        midi_slider.setMinimum(0)
        midi_slider.setMaximum(100)
        midi_slider.setValue(80)
        midi_slider_layout.addWidget(midi_slider)
        
        midi_value_label = QLabel("2.00mm (80)")
        midi_value_label.setMinimumWidth(100)
        midi_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_slider_layout.addWidget(midi_value_label)
        
        advanced_layout.addLayout(midi_slider_layout)
        midi_slider.valueChanged.connect(
            lambda v, lbl=midi_value_label: self.on_master_slider_changed('midi', v, lbl)
        )
        
        # Aftertouch Mode (dropdown)
        combo_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Aftertouch Mode:"))
        label.setMinimumWidth(200)
        combo_layout.addWidget(label)
        
        aftertouch_combo = ArrowComboBox()
        aftertouch_combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        aftertouch_combo.addItem("Off", 0)
        aftertouch_combo.addItem("Reverse", 1)
        aftertouch_combo.addItem("Bottom-Out", 2)
        aftertouch_combo.addItem("Post-Actuation", 3)
        aftertouch_combo.addItem("Vibrato", 4)
        aftertouch_combo.setCurrentIndex(0)
        aftertouch_combo.setEditable(True)
        aftertouch_combo.lineEdit().setReadOnly(True)
        aftertouch_combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(aftertouch_combo)
        combo_layout.addStretch()
        
        advanced_layout.addLayout(combo_layout)
        aftertouch_combo.currentIndexChanged.connect(
            lambda: self.on_master_combo_changed('aftertouch', aftertouch_combo)
        )
        
        # Aftertouch CC (dropdown)
        combo_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Aftertouch CC:"))
        label.setMinimumWidth(200)
        combo_layout.addWidget(label)
        
        aftertouch_cc_combo = ArrowComboBox()
        aftertouch_cc_combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        aftertouch_cc_combo.addItem("Off", 255)  # 255 = no CC sent, only poly aftertouch
        for cc in range(128):
            aftertouch_cc_combo.addItem(f"CC#{cc}", cc)
        aftertouch_cc_combo.setCurrentIndex(0)  # Default: Off
        aftertouch_cc_combo.setEditable(True)
        aftertouch_cc_combo.lineEdit().setReadOnly(True)
        aftertouch_cc_combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(aftertouch_cc_combo)
        combo_layout.addStretch()

        advanced_layout.addLayout(combo_layout)
        aftertouch_cc_combo.currentIndexChanged.connect(
            lambda: self.on_master_combo_changed('aftertouch_cc', aftertouch_cc_combo)
        )
        
        # Velocity Mode (dropdown)
        combo_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Velocity Mode:"))
        label.setMinimumWidth(200)
        combo_layout.addWidget(label)
        
        velocity_combo = ArrowComboBox()
        velocity_combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        velocity_combo.addItem("Fixed (64)", 0)
        velocity_combo.addItem("Peak at Apex", 1)
        velocity_combo.addItem("Speed-Based", 2)
        velocity_combo.addItem("Speed + Peak Combined", 3)
        velocity_combo.setCurrentIndex(2)
        velocity_combo.setEditable(True)
        velocity_combo.lineEdit().setReadOnly(True)
        velocity_combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(velocity_combo)
        combo_layout.addStretch()
        
        advanced_layout.addLayout(combo_layout)
        velocity_combo.currentIndexChanged.connect(
            lambda: self.on_master_combo_changed('velocity', velocity_combo)
        )
        
        # Velocity Speed Scale (dropdown)
        combo_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Velocity Speed Scale:"))
        label.setMinimumWidth(200)
        combo_layout.addWidget(label)
        
        vel_speed_combo = ArrowComboBox()
        vel_speed_combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        for i in range(1, 21):
            vel_speed_combo.addItem(str(i), i)
        vel_speed_combo.setCurrentIndex(9)
        vel_speed_combo.setEditable(True)
        vel_speed_combo.lineEdit().setReadOnly(True)
        vel_speed_combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(vel_speed_combo)
        combo_layout.addStretch()
        
        advanced_layout.addLayout(combo_layout)
        vel_speed_combo.currentIndexChanged.connect(
            lambda: self.on_master_combo_changed('vel_speed', vel_speed_combo)
        )
        
        # Enable MIDI Rapidfire checkbox
        midi_rapid_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Enable MIDI Rapidfire"))
        midi_rapid_checkbox.setChecked(False)
        advanced_layout.addWidget(midi_rapid_checkbox)
        midi_rapid_checkbox.stateChanged.connect(self.on_midi_rapidfire_toggled)
        
        # MIDI Rapidfire Sensitivity (slider) - hidden by default
        midi_rapid_sens_layout = QHBoxLayout()
        midi_rapid_sens_label = QLabel(tr("LayerActuationConfigurator", "MIDI Rapidfire Sensitivity:"))
        midi_rapid_sens_label.setMinimumWidth(200)
        midi_rapid_sens_layout.addWidget(midi_rapid_sens_label)
        
        midi_rapid_sens_slider = QSlider(Qt.Horizontal)
        midi_rapid_sens_slider.setMinimum(1)
        midi_rapid_sens_slider.setMaximum(100)
        midi_rapid_sens_slider.setValue(10)
        midi_rapid_sens_layout.addWidget(midi_rapid_sens_slider)
        
        midi_rapid_sens_value_label = QLabel("10")
        midi_rapid_sens_value_label.setMinimumWidth(100)
        midi_rapid_sens_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_rapid_sens_layout.addWidget(midi_rapid_sens_value_label)
        
        midi_rapid_sens_widget = QWidget()
        midi_rapid_sens_widget.setLayout(midi_rapid_sens_layout)
        midi_rapid_sens_widget.setVisible(False)
        advanced_layout.addWidget(midi_rapid_sens_widget)
        
        midi_rapid_sens_slider.valueChanged.connect(
            lambda v, lbl=midi_rapid_sens_value_label: self.on_master_slider_changed('midi_rapid_sens', v, lbl)
        )
        
        # MIDI Rapidfire Velocity Range (slider) - hidden by default
        midi_rapid_vel_layout = QHBoxLayout()
        midi_rapid_vel_label = QLabel(tr("LayerActuationConfigurator", "MIDI Rapidfire Velocity Range:"))
        midi_rapid_vel_label.setMinimumWidth(200)
        midi_rapid_vel_layout.addWidget(midi_rapid_vel_label)
        
        midi_rapid_vel_slider = QSlider(Qt.Horizontal)
        midi_rapid_vel_slider.setMinimum(0)
        midi_rapid_vel_slider.setMaximum(20)
        midi_rapid_vel_slider.setValue(10)
        midi_rapid_vel_layout.addWidget(midi_rapid_vel_slider)
        
        midi_rapid_vel_value_label = QLabel("±10")
        midi_rapid_vel_value_label.setMinimumWidth(100)
        midi_rapid_vel_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_rapid_vel_layout.addWidget(midi_rapid_vel_value_label)
        
        midi_rapid_vel_widget = QWidget()
        midi_rapid_vel_widget.setLayout(midi_rapid_vel_layout)
        midi_rapid_vel_widget.setVisible(False)
        advanced_layout.addWidget(midi_rapid_vel_widget)
        
        midi_rapid_vel_slider.valueChanged.connect(
            lambda v, lbl=midi_rapid_vel_value_label: self.on_master_slider_changed('midi_rapid_vel', v, lbl)
        )

        # === HE VELOCITY CONTROLS ===
        # Add separator
        he_line = QFrame()
        he_line.setFrameShape(QFrame.HLine)
        he_line.setFrameShadow(QFrame.Sunken)
        advanced_layout.addWidget(he_line)

        # Use Fixed Velocity checkbox
        use_fixed_vel_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Use Fixed Velocity"))
        use_fixed_vel_checkbox.setChecked(False)
        use_fixed_vel_checkbox.setStyleSheet("QCheckBox { font-size: 10px; }")
        advanced_layout.addWidget(use_fixed_vel_checkbox)
        use_fixed_vel_checkbox.stateChanged.connect(self.on_use_fixed_velocity_toggled)

        # HE Velocity Curve (dropdown)
        curve_layout = QHBoxLayout()
        curve_label = QLabel(tr("LayerActuationConfigurator", "HE Velocity Curve:"))
        curve_label.setMinimumWidth(200)
        curve_layout.addWidget(curve_label)

        he_curve_combo = ArrowComboBox()
        he_curve_combo.setMinimumHeight(30)
        he_curve_combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; font-size: 12px; } QComboBox QAbstractItemView { min-height: 125px; }")
        # Factory curves (0-6)
        he_curve_combo.addItem("Linear", 0)
        he_curve_combo.addItem("Aggro", 1)
        he_curve_combo.addItem("Slow", 2)
        he_curve_combo.addItem("Smooth", 3)
        he_curve_combo.addItem("Steep", 4)
        he_curve_combo.addItem("Instant", 5)
        he_curve_combo.addItem("Turbo", 6)
        # User curves (7-16)
        for i in range(10):
            he_curve_combo.addItem(f"User {i+1}", 7 + i)
        he_curve_combo.setCurrentIndex(0)  # Default: Linear
        he_curve_combo.setEditable(True)
        he_curve_combo.lineEdit().setReadOnly(True)
        he_curve_combo.lineEdit().setAlignment(Qt.AlignCenter)
        curve_layout.addWidget(he_curve_combo)
        curve_layout.addStretch()

        advanced_layout.addLayout(curve_layout)
        he_curve_combo.currentIndexChanged.connect(
            lambda: self.on_master_combo_changed('he_curve', he_curve_combo)
        )

        # HE Velocity Min (slider)
        he_min_layout = QHBoxLayout()
        he_min_label = QLabel(tr("LayerActuationConfigurator", "HE Velocity Min:"))
        he_min_label.setMinimumWidth(200)
        he_min_layout.addWidget(he_min_label)

        he_min_slider = QSlider(Qt.Horizontal)
        he_min_slider.setMinimum(1)
        he_min_slider.setMaximum(127)
        he_min_slider.setValue(1)
        he_min_layout.addWidget(he_min_slider)

        he_min_value_label = QLabel("1")
        he_min_value_label.setMinimumWidth(100)
        he_min_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        he_min_layout.addWidget(he_min_value_label)

        advanced_layout.addLayout(he_min_layout)
        he_min_slider.valueChanged.connect(
            lambda v, lbl=he_min_value_label: self.on_master_slider_changed('he_min', v, lbl)
        )

        # HE Velocity Max (slider)
        he_max_layout = QHBoxLayout()
        he_max_label = QLabel(tr("LayerActuationConfigurator", "HE Velocity Max:"))
        he_max_label.setMinimumWidth(200)
        he_max_layout.addWidget(he_max_label)

        he_max_slider = QSlider(Qt.Horizontal)
        he_max_slider.setMinimum(1)
        he_max_slider.setMaximum(127)
        he_max_slider.setValue(127)
        he_max_layout.addWidget(he_max_slider)

        he_max_value_label = QLabel("127")
        he_max_value_label.setMinimumWidth(100)
        he_max_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        he_max_layout.addWidget(he_max_value_label)

        advanced_layout.addLayout(he_max_layout)
        he_max_slider.valueChanged.connect(
            lambda v, lbl=he_max_value_label: self.on_master_slider_changed('he_max', v, lbl)
        )

        # Add the MIDI settings layout to the content container
        content_container.addLayout(advanced_layout, 1)

        # Create KeySplit offshoot window
        self.keysplit_actuation_offshoot = QGroupBox(tr("LayerActuationConfigurator", "KeySplit Settings"))
        self.keysplit_actuation_offshoot.setMaximumWidth(300)
        keysplit_layout = QGridLayout()
        keysplit_layout.setVerticalSpacing(10)
        keysplit_layout.setHorizontalSpacing(10)
        self.keysplit_actuation_offshoot.setLayout(keysplit_layout)

        ks_row = 0
        keysplit_layout.addWidget(QLabel(tr("LayerActuationConfigurator", "Sustain:")), ks_row, 0)
        self.keysplit_actuation_sustain = ArrowComboBox()
        self.keysplit_actuation_sustain.setMinimumWidth(80)
        self.keysplit_actuation_sustain.setMaximumWidth(120)
        self.keysplit_actuation_sustain.setMinimumHeight(25)
        self.keysplit_actuation_sustain.setMaximumHeight(25)
        self.keysplit_actuation_sustain.addItem("Ignore", 0)
        self.keysplit_actuation_sustain.addItem("Allow", 1)
        self.keysplit_actuation_sustain.setCurrentIndex(0)
        self.keysplit_actuation_sustain.setEditable(True)
        self.keysplit_actuation_sustain.lineEdit().setReadOnly(True)
        self.keysplit_actuation_sustain.lineEdit().setAlignment(Qt.AlignCenter)
        keysplit_layout.addWidget(self.keysplit_actuation_sustain, ks_row, 1)

        self.keysplit_actuation_offshoot.hide()

        # TripleSplit offshoot window
        self.triplesplit_actuation_offshoot = QGroupBox(tr("LayerActuationConfigurator", "TripleSplit Settings"))
        self.triplesplit_actuation_offshoot.setMaximumWidth(300)
        triplesplit_layout = QGridLayout()
        triplesplit_layout.setVerticalSpacing(10)
        triplesplit_layout.setHorizontalSpacing(10)
        self.triplesplit_actuation_offshoot.setLayout(triplesplit_layout)

        ts_row = 0
        triplesplit_layout.addWidget(QLabel(tr("LayerActuationConfigurator", "Sustain:")), ts_row, 0)
        self.triplesplit_actuation_sustain = ArrowComboBox()
        self.triplesplit_actuation_sustain.setMinimumWidth(80)
        self.triplesplit_actuation_sustain.setMaximumWidth(120)
        self.triplesplit_actuation_sustain.setMinimumHeight(25)
        self.triplesplit_actuation_sustain.setMaximumHeight(25)
        self.triplesplit_actuation_sustain.addItem("Ignore", 0)
        self.triplesplit_actuation_sustain.addItem("Allow", 1)
        self.triplesplit_actuation_sustain.setCurrentIndex(0)
        self.triplesplit_actuation_sustain.setEditable(True)
        self.triplesplit_actuation_sustain.lineEdit().setReadOnly(True)
        self.triplesplit_actuation_sustain.lineEdit().setAlignment(Qt.AlignCenter)
        triplesplit_layout.addWidget(self.triplesplit_actuation_sustain, ts_row, 1)

        self.triplesplit_actuation_offshoot.hide()

        # Add offshoots to content container (side by side)
        content_container.addWidget(self.keysplit_actuation_offshoot)
        content_container.addWidget(self.triplesplit_actuation_offshoot)

        # Add content container to main advanced layout
        advanced_layout_main.addLayout(content_container)

        layout.addWidget(self.advanced_widget)
        
        # Store widgets
        self.master_widgets = {
            'normal_slider': normal_slider,
            'normal_label': normal_value_label,
            'midi_slider': midi_slider,
            'midi_label': midi_value_label,
            'aftertouch_combo': aftertouch_combo,
            'aftertouch_cc_combo': aftertouch_cc_combo,
            'velocity_combo': velocity_combo,
            'vel_speed_combo': vel_speed_combo,
            'rapid_checkbox': rapid_checkbox,
            'rapid_slider': rapid_slider,
            'rapid_label': rapid_value_label,
            'rapid_widget': rapid_slider_widget,
            'midi_rapid_checkbox': midi_rapid_checkbox,
            'midi_rapid_sens_slider': midi_rapid_sens_slider,
            'midi_rapid_sens_label': midi_rapid_sens_value_label,
            'midi_rapid_sens_widget': midi_rapid_sens_widget,
            'midi_rapid_vel_slider': midi_rapid_vel_slider,
            'midi_rapid_vel_label': midi_rapid_vel_value_label,
            'midi_rapid_vel_widget': midi_rapid_vel_widget,
            # HE Velocity controls
            'use_fixed_vel_checkbox': use_fixed_vel_checkbox,
            'he_curve_combo': he_curve_combo,
            'he_min_slider': he_min_slider,
            'he_min_label': he_min_value_label,
            'he_max_slider': he_max_slider,
            'he_max_label': he_max_value_label
        }
        
        return group
    
    def create_layer_group(self):
        """Create a group for the currently selected layer's settings"""
        group = QGroupBox(tr("LayerActuationConfigurator", f"Layer {self.current_layer} Settings"))
        group.setMaximumWidth(500)
        group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 11px; }")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        group.setLayout(layout)
        
        # Show Advanced Options checkbox
        layer_advanced_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Show Advanced Actuation Options"))
        layer_advanced_checkbox.setStyleSheet("QCheckBox { font-size: 11px; margin-bottom: 5px; }")
        layer_advanced_checkbox.stateChanged.connect(self.on_layer_advanced_toggled)
        layout.addWidget(layer_advanced_checkbox)
        
        # Add separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Normal actuation slider - ALWAYS VISIBLE
        normal_slider_layout = QHBoxLayout()
        normal_label = QLabel(tr("LayerActuationConfigurator", "Normal Keys Actuation:"))
        normal_label.setMinimumWidth(180)
        normal_slider_layout.addWidget(normal_label)
        
        normal_slider = QSlider(Qt.Horizontal)
        normal_slider.setMinimum(0)
        normal_slider.setMaximum(100)
        normal_slider.setValue(80)
        normal_slider_layout.addWidget(normal_slider)
        
        normal_value_label = QLabel("2.00mm (80)")
        normal_value_label.setMinimumWidth(100)
        normal_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        normal_slider_layout.addWidget(normal_value_label)
        
        layout.addLayout(normal_slider_layout)
        normal_slider.valueChanged.connect(
            lambda v, lbl=normal_value_label: self.on_layer_slider_changed('normal', v, lbl)
        )
        self.layer_widgets['normal_slider'] = normal_slider
        self.layer_widgets['normal_label'] = normal_value_label
        
        # Enable Rapidfire checkbox - ALWAYS VISIBLE
        rapid_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Enable Rapidfire"))
        rapid_checkbox.setStyleSheet("QCheckBox { font-size: 10px; }")
        layout.addWidget(rapid_checkbox)
        self.layer_widgets['rapid_checkbox'] = rapid_checkbox
        
        # Rapidfire Sensitivity slider - hidden by default
        rapid_sens_slider_layout = QHBoxLayout()
        rapid_sens_label = QLabel(tr("LayerActuationConfigurator", "Rapidfire Sensitivity:"))
        rapid_sens_label.setMinimumWidth(180)
        rapid_sens_slider_layout.addWidget(rapid_sens_label)
        
        rapid_sens_slider = QSlider(Qt.Horizontal)
        rapid_sens_slider.setMinimum(1)
        rapid_sens_slider.setMaximum(100)
        rapid_sens_slider.setValue(4)
        rapid_sens_slider_layout.addWidget(rapid_sens_slider)
        
        rapid_sens_value_label = QLabel("4")
        rapid_sens_value_label.setMinimumWidth(100)
        rapid_sens_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        rapid_sens_slider_layout.addWidget(rapid_sens_value_label)
        
        rapid_widget = QWidget()
        rapid_widget.setLayout(rapid_sens_slider_layout)
        rapid_widget.setVisible(False)
        layout.addWidget(rapid_widget)
        
        rapid_sens_slider.valueChanged.connect(
            lambda v, lbl=rapid_sens_value_label: self.on_layer_slider_changed('rapid', v, lbl)
        )
        self.layer_widgets['rapid_slider'] = rapid_sens_slider
        self.layer_widgets['rapid_label'] = rapid_sens_value_label
        self.layer_widgets['rapid_widget'] = rapid_widget
        
        rapid_checkbox.stateChanged.connect(
            lambda state: rapid_widget.setVisible(state == Qt.Checked)
        )
        
        # === ADVANCED OPTIONS (hidden by default) ===
        layer_advanced_widget = QWidget()
        layer_advanced_layout = QVBoxLayout()
        layer_advanced_layout.setSpacing(8)
        layer_advanced_layout.setContentsMargins(0, 10, 0, 0)
        layer_advanced_widget.setLayout(layer_advanced_layout)
        layer_advanced_widget.setVisible(False)
        
        # Add separator
        adv_line = QFrame()
        adv_line.setFrameShape(QFrame.HLine)
        adv_line.setFrameShadow(QFrame.Sunken)
        layer_advanced_layout.addWidget(adv_line)
        
        # MIDI actuation slider
        midi_slider_layout = QHBoxLayout()
        midi_label = QLabel(tr("LayerActuationConfigurator", "MIDI Keys Actuation:"))
        midi_label.setMinimumWidth(180)
        midi_slider_layout.addWidget(midi_label)
        
        midi_slider = QSlider(Qt.Horizontal)
        midi_slider.setMinimum(0)
        midi_slider.setMaximum(100)
        midi_slider.setValue(80)
        midi_slider_layout.addWidget(midi_slider)
        
        midi_value_label = QLabel("2.00mm (80)")
        midi_value_label.setMinimumWidth(100)
        midi_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_slider_layout.addWidget(midi_value_label)
        
        layer_advanced_layout.addLayout(midi_slider_layout)
        midi_slider.valueChanged.connect(
            lambda v, lbl=midi_value_label: self.on_layer_slider_changed('midi', v, lbl)
        )
        self.layer_widgets['midi_slider'] = midi_slider
        self.layer_widgets['midi_label'] = midi_value_label
        
        # Aftertouch Mode combo
        combo_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Aftertouch Mode:"))
        label.setMinimumWidth(180)
        combo_layout.addWidget(label)
        
        combo = ArrowComboBox()
        combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        combo.addItem("Off", 0)
        combo.addItem("Reverse", 1)
        combo.addItem("Bottom-Out", 2)
        combo.addItem("Post-Actuation", 3)
        combo.addItem("Vibrato", 4)
        combo.setEditable(True)
        combo.lineEdit().setReadOnly(True)
        combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(combo)
        combo_layout.addStretch()

        layer_advanced_layout.addLayout(combo_layout)
        combo.currentIndexChanged.connect(
            lambda: self.on_layer_combo_changed('aftertouch', combo)
        )
        self.layer_widgets['aftertouch_combo'] = combo
        
        # Aftertouch CC combo
        combo_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Aftertouch CC:"))
        label.setMinimumWidth(180)
        combo_layout.addWidget(label)
        
        combo = ArrowComboBox()
        combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        combo.addItem("Off", 255)  # 255 = no CC sent, only poly aftertouch
        for cc in range(128):
            combo.addItem(f"CC#{cc}", cc)
        combo.setCurrentIndex(0)  # Default: Off
        combo.setEditable(True)
        combo.lineEdit().setReadOnly(True)
        combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(combo)
        combo_layout.addStretch()

        layer_advanced_layout.addLayout(combo_layout)
        combo.currentIndexChanged.connect(
            lambda: self.on_layer_combo_changed('aftertouch_cc', combo)
        )
        self.layer_widgets['aftertouch_cc_combo'] = combo
        
        # Velocity Mode combo
        combo_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Velocity Mode:"))
        label.setMinimumWidth(180)
        combo_layout.addWidget(label)
        
        combo = ArrowComboBox()
        combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        combo.addItem("Fixed (64)", 0)
        combo.addItem("Peak at Apex", 1)
        combo.addItem("Speed-Based", 2)
        combo.addItem("Speed + Peak Combined", 3)
        combo.setCurrentIndex(2)
        combo.setEditable(True)
        combo.lineEdit().setReadOnly(True)
        combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(combo)
        combo_layout.addStretch()

        layer_advanced_layout.addLayout(combo_layout)
        combo.currentIndexChanged.connect(
            lambda: self.on_layer_combo_changed('velocity', combo)
        )
        self.layer_widgets['velocity_combo'] = combo
        
        # Velocity Speed Scale combo
        combo_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Velocity Speed Scale:"))
        label.setMinimumWidth(180)
        combo_layout.addWidget(label)
        
        combo = ArrowComboBox()
        combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        for i in range(1, 21):
            combo.addItem(str(i), i)
        combo.setCurrentIndex(9)
        combo.setEditable(True)
        combo.lineEdit().setReadOnly(True)
        combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(combo)
        combo_layout.addStretch()

        layer_advanced_layout.addLayout(combo_layout)
        combo.currentIndexChanged.connect(
            lambda: self.on_layer_combo_changed('vel_speed', combo)
        )
        self.layer_widgets['vel_speed_combo'] = combo
        
        # Enable MIDI Rapidfire checkbox
        midi_rapid_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Enable MIDI Rapidfire"))
        midi_rapid_checkbox.setStyleSheet("QCheckBox { font-size: 10px; }")
        layer_advanced_layout.addWidget(midi_rapid_checkbox)
        self.layer_widgets['midi_rapid_checkbox'] = midi_rapid_checkbox
        
        # MIDI Rapidfire Sensitivity slider - hidden by default
        midi_rapid_sens_slider_layout = QHBoxLayout()
        midi_rapid_sens_label = QLabel(tr("LayerActuationConfigurator", "MIDI Rapidfire Sensitivity:"))
        midi_rapid_sens_label.setMinimumWidth(180)
        midi_rapid_sens_slider_layout.addWidget(midi_rapid_sens_label)
        
        midi_rapid_sens_slider = QSlider(Qt.Horizontal)
        midi_rapid_sens_slider.setMinimum(1)
        midi_rapid_sens_slider.setMaximum(100)
        midi_rapid_sens_slider.setValue(10)
        midi_rapid_sens_slider_layout.addWidget(midi_rapid_sens_slider)
        
        midi_rapid_sens_value_label = QLabel("10")
        midi_rapid_sens_value_label.setMinimumWidth(100)
        midi_rapid_sens_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_rapid_sens_slider_layout.addWidget(midi_rapid_sens_value_label)
        
        midi_rapid_sens_widget = QWidget()
        midi_rapid_sens_widget.setLayout(midi_rapid_sens_slider_layout)
        midi_rapid_sens_widget.setVisible(False)
        layer_advanced_layout.addWidget(midi_rapid_sens_widget)
        
        midi_rapid_sens_slider.valueChanged.connect(
            lambda v, lbl=midi_rapid_sens_value_label: self.on_layer_slider_changed('midi_rapid_sens', v, lbl)
        )
        self.layer_widgets['midi_rapid_sens_slider'] = midi_rapid_sens_slider
        self.layer_widgets['midi_rapid_sens_label'] = midi_rapid_sens_value_label
        self.layer_widgets['midi_rapid_sens_widget'] = midi_rapid_sens_widget
        
        # MIDI Rapidfire Velocity Range slider - hidden by default
        midi_rapid_vel_slider_layout = QHBoxLayout()
        midi_rapid_vel_label = QLabel(tr("LayerActuationConfigurator", "MIDI Rapidfire Velocity Range:"))
        midi_rapid_vel_label.setMinimumWidth(180)
        midi_rapid_vel_slider_layout.addWidget(midi_rapid_vel_label)
        
        midi_rapid_vel_slider = QSlider(Qt.Horizontal)
        midi_rapid_vel_slider.setMinimum(0)
        midi_rapid_vel_slider.setMaximum(20)
        midi_rapid_vel_slider.setValue(10)
        midi_rapid_vel_slider_layout.addWidget(midi_rapid_vel_slider)
        
        midi_rapid_vel_value_label = QLabel("±10")
        midi_rapid_vel_value_label.setMinimumWidth(100)
        midi_rapid_vel_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_rapid_vel_slider_layout.addWidget(midi_rapid_vel_value_label)
        
        midi_rapid_vel_widget = QWidget()
        midi_rapid_vel_widget.setLayout(midi_rapid_vel_slider_layout)
        midi_rapid_vel_widget.setVisible(False)
        layer_advanced_layout.addWidget(midi_rapid_vel_widget)
        
        midi_rapid_vel_slider.valueChanged.connect(
            lambda v, lbl=midi_rapid_vel_value_label: self.on_layer_slider_changed('midi_rapid_vel', v, lbl)
        )
        self.layer_widgets['midi_rapid_vel_slider'] = midi_rapid_vel_slider
        self.layer_widgets['midi_rapid_vel_label'] = midi_rapid_vel_value_label
        self.layer_widgets['midi_rapid_vel_widget'] = midi_rapid_vel_widget
        
        # Connect checkbox to show/hide both MIDI rapidfire widgets
        def toggle_midi_rapid_widgets(state):
            enabled = (state == Qt.Checked)
            midi_rapid_sens_widget.setVisible(enabled)
            midi_rapid_vel_widget.setVisible(enabled)
        
        midi_rapid_checkbox.stateChanged.connect(toggle_midi_rapid_widgets)

        # === HE VELOCITY CONTROLS (PER-LAYER) ===
        # Add separator
        he_line = QFrame()
        he_line.setFrameShape(QFrame.HLine)
        he_line.setFrameShadow(QFrame.Sunken)
        layer_advanced_layout.addWidget(he_line)

        # Use Fixed Velocity checkbox
        use_fixed_vel_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Use Fixed Velocity"))
        use_fixed_vel_checkbox.setChecked(False)
        use_fixed_vel_checkbox.setStyleSheet("QCheckBox { font-size: 10px; }")
        layer_advanced_layout.addWidget(use_fixed_vel_checkbox)
        self.layer_widgets['use_fixed_vel_checkbox'] = use_fixed_vel_checkbox

        # HE Velocity Curve (dropdown)
        curve_layout = QHBoxLayout()
        curve_label = QLabel(tr("LayerActuationConfigurator", "HE Velocity Curve:"))
        curve_label.setMinimumWidth(180)
        curve_layout.addWidget(curve_label)

        he_curve_combo = ArrowComboBox()
        he_curve_combo.setMinimumHeight(30)
        he_curve_combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; font-size: 12px; } QComboBox QAbstractItemView { min-height: 125px; }")
        # Factory curves (0-6)
        he_curve_combo.addItem("Linear", 0)
        he_curve_combo.addItem("Aggro", 1)
        he_curve_combo.addItem("Slow", 2)
        he_curve_combo.addItem("Smooth", 3)
        he_curve_combo.addItem("Steep", 4)
        he_curve_combo.addItem("Instant", 5)
        he_curve_combo.addItem("Turbo", 6)
        # User curves (7-16)
        for i in range(10):
            he_curve_combo.addItem(f"User {i+1}", 7 + i)
        he_curve_combo.setCurrentIndex(0)  # Default: Linear
        he_curve_combo.setEditable(True)
        he_curve_combo.lineEdit().setReadOnly(True)
        he_curve_combo.lineEdit().setAlignment(Qt.AlignCenter)
        curve_layout.addWidget(he_curve_combo)
        curve_layout.addStretch()

        layer_advanced_layout.addLayout(curve_layout)
        he_curve_combo.currentIndexChanged.connect(
            lambda: self.on_layer_combo_changed('he_curve', he_curve_combo)
        )
        self.layer_widgets['he_curve_combo'] = he_curve_combo

        # HE Velocity Min (slider)
        he_min_layout = QHBoxLayout()
        he_min_label = QLabel(tr("LayerActuationConfigurator", "HE Velocity Min:"))
        he_min_label.setMinimumWidth(180)
        he_min_layout.addWidget(he_min_label)

        he_min_slider = QSlider(Qt.Horizontal)
        he_min_slider.setMinimum(1)
        he_min_slider.setMaximum(127)
        he_min_slider.setValue(1)
        he_min_layout.addWidget(he_min_slider)

        he_min_value_label = QLabel("1")
        he_min_value_label.setMinimumWidth(100)
        he_min_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        he_min_layout.addWidget(he_min_value_label)

        layer_advanced_layout.addLayout(he_min_layout)
        he_min_slider.valueChanged.connect(
            lambda v, lbl=he_min_value_label: self.on_layer_slider_changed('he_min', v, lbl)
        )
        self.layer_widgets['he_min_slider'] = he_min_slider
        self.layer_widgets['he_min_label'] = he_min_value_label

        # HE Velocity Max (slider)
        he_max_layout = QHBoxLayout()
        he_max_label = QLabel(tr("LayerActuationConfigurator", "HE Velocity Max:"))
        he_max_label.setMinimumWidth(180)
        he_max_layout.addWidget(he_max_label)

        he_max_slider = QSlider(Qt.Horizontal)
        he_max_slider.setMinimum(1)
        he_max_slider.setMaximum(127)
        he_max_slider.setValue(127)
        he_max_layout.addWidget(he_max_slider)

        he_max_value_label = QLabel("127")
        he_max_value_label.setMinimumWidth(100)
        he_max_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        he_max_layout.addWidget(he_max_value_label)

        layer_advanced_layout.addLayout(he_max_layout)
        he_max_slider.valueChanged.connect(
            lambda v, lbl=he_max_value_label: self.on_layer_slider_changed('he_max', v, lbl)
        )
        self.layer_widgets['he_max_slider'] = he_max_slider
        self.layer_widgets['he_max_label'] = he_max_value_label

        layout.addWidget(layer_advanced_widget)
        self.layer_widgets['advanced_widget'] = layer_advanced_widget
        self.layer_widgets['advanced_checkbox'] = layer_advanced_checkbox
        self.layer_widgets['group'] = group
        
        return group
    
    def on_advanced_toggled(self):
        """Show/hide advanced options in master controls"""
        self.advanced_shown = self.advanced_checkbox.isChecked()
        self.advanced_widget.setVisible(self.advanced_shown)

    def on_actuation_split_mode_changed(self):
        """Show/hide split offshoots based on split mode"""
        if not hasattr(self, 'actuation_split_mode'):
            return

        split_status = self.actuation_split_mode.currentData()

        # Show/hide offshoot windows based on split mode
        if split_status == 0:  # No splits
            self.keysplit_actuation_offshoot.hide()
            self.triplesplit_actuation_offshoot.hide()
        elif split_status == 1:  # KeySplit only
            self.keysplit_actuation_offshoot.show()
            self.triplesplit_actuation_offshoot.hide()
        elif split_status == 2:  # TripleSplit only
            self.keysplit_actuation_offshoot.hide()
            self.triplesplit_actuation_offshoot.show()
        elif split_status == 3:  # Both splits
            self.keysplit_actuation_offshoot.show()
            self.triplesplit_actuation_offshoot.show()

    def on_layer_advanced_toggled(self):
        """Show/hide advanced options in layer controls"""
        shown = self.layer_widgets['advanced_checkbox'].isChecked()
        self.layer_widgets['advanced_widget'].setVisible(shown)
    
    def on_per_layer_toggled(self):
        """Handle master per-layer checkbox toggle"""
        self.per_layer_enabled = self.per_layer_checkbox.isChecked()
        self.layer_selector_container.setVisible(self.per_layer_enabled)
        
        # Enable/disable master controls based on per-layer mode
        self.master_group.setEnabled(not self.per_layer_enabled)
        
        if not self.per_layer_enabled:
            self.sync_all_to_master()
        else:
            # Load current layer data into UI
            self.load_layer_to_ui(self.current_layer)
    
    def on_layer_changed(self, index):
        """Handle layer dropdown change"""
        # Save current layer data from UI
        self.save_ui_to_layer(self.current_layer)
        
        # Update current layer
        self.current_layer = index
        
        # Update group title
        self.layer_widgets['group'].setTitle(tr("LayerActuationConfigurator", f"Layer {self.current_layer} Settings"))
        
        # Load new layer data to UI
        self.load_layer_to_ui(self.current_layer)
    
    def save_ui_to_layer(self, layer):
        """Save current UI values to layer data"""
        self.layer_data[layer]['normal'] = self.layer_widgets['normal_slider'].value()
        self.layer_data[layer]['midi'] = self.layer_widgets['midi_slider'].value()
        self.layer_data[layer]['aftertouch'] = self.layer_widgets['aftertouch_combo'].currentData()
        self.layer_data[layer]['velocity'] = self.layer_widgets['velocity_combo'].currentData()
        self.layer_data[layer]['rapid'] = self.layer_widgets['rapid_slider'].value()
        self.layer_data[layer]['midi_rapid_sens'] = self.layer_widgets['midi_rapid_sens_slider'].value()
        self.layer_data[layer]['midi_rapid_vel'] = self.layer_widgets['midi_rapid_vel_slider'].value()
        self.layer_data[layer]['vel_speed'] = self.layer_widgets['vel_speed_combo'].currentData()
        self.layer_data[layer]['aftertouch_cc'] = self.layer_widgets['aftertouch_cc_combo'].currentData()
        self.layer_data[layer]['rapidfire_enabled'] = self.layer_widgets['rapid_checkbox'].isChecked()
        self.layer_data[layer]['midi_rapidfire_enabled'] = self.layer_widgets['midi_rapid_checkbox'].isChecked()
        # HE Velocity fields
        self.layer_data[layer]['use_fixed_velocity'] = self.layer_widgets['use_fixed_vel_checkbox'].isChecked()
        self.layer_data[layer]['he_curve'] = self.layer_widgets['he_curve_combo'].currentData()
        self.layer_data[layer]['he_min'] = self.layer_widgets['he_min_slider'].value()
        self.layer_data[layer]['he_max'] = self.layer_widgets['he_max_slider'].value()
    
    def load_layer_to_ui(self, layer):
        """Load layer data to UI"""
        data = self.layer_data[layer]

        # Set sliders
        self.layer_widgets['normal_slider'].setValue(data['normal'])
        self.layer_widgets['midi_slider'].setValue(data['midi'])

        # Set combos
        for key in ['aftertouch', 'aftertouch_cc', 'velocity', 'vel_speed', 'he_curve']:
            combo = self.layer_widgets[f'{key}_combo']
            for i in range(combo.count()):
                if combo.itemData(i) == data[key]:
                    combo.setCurrentIndex(i)
                    break

        # Set rapidfire
        self.layer_widgets['rapid_checkbox'].setChecked(data['rapidfire_enabled'])
        self.layer_widgets['rapid_widget'].setVisible(data['rapidfire_enabled'])
        self.layer_widgets['rapid_slider'].setValue(data['rapid'])

        # Set MIDI rapidfire
        self.layer_widgets['midi_rapid_checkbox'].setChecked(data['midi_rapidfire_enabled'])
        self.layer_widgets['midi_rapid_sens_widget'].setVisible(data['midi_rapidfire_enabled'])
        self.layer_widgets['midi_rapid_vel_widget'].setVisible(data['midi_rapidfire_enabled'])
        self.layer_widgets['midi_rapid_sens_slider'].setValue(data['midi_rapid_sens'])
        self.layer_widgets['midi_rapid_vel_slider'].setValue(data['midi_rapid_vel'])

        # Set HE Velocity settings
        self.layer_widgets['use_fixed_vel_checkbox'].setChecked(data['use_fixed_velocity'])
        self.layer_widgets['he_min_slider'].setValue(data['he_min'])
        self.layer_widgets['he_max_slider'].setValue(data['he_max'])
    
    def on_rapidfire_toggled(self):
        """Show/hide rapidfire sensitivity based on checkbox"""
        enabled = self.master_widgets['rapid_checkbox'].isChecked()
        self.master_widgets['rapid_widget'].setVisible(enabled)
        
        if not self.per_layer_enabled:
            for layer_data in self.layer_data:
                layer_data['rapidfire_enabled'] = enabled
    
    def on_midi_rapidfire_toggled(self):
        """Show/hide MIDI rapidfire widgets based on checkbox"""
        enabled = self.master_widgets['midi_rapid_checkbox'].isChecked()
        self.master_widgets['midi_rapid_sens_widget'].setVisible(enabled)
        self.master_widgets['midi_rapid_vel_widget'].setVisible(enabled)

        if not self.per_layer_enabled:
            for layer_data in self.layer_data:
                layer_data['midi_rapidfire_enabled'] = enabled

    def on_use_fixed_velocity_toggled(self):
        """Handle Use Fixed Velocity checkbox toggle"""
        enabled = self.master_widgets['use_fixed_vel_checkbox'].isChecked()

        if not self.per_layer_enabled:
            for layer_data in self.layer_data:
                layer_data['use_fixed_velocity'] = enabled
    
    def on_master_slider_changed(self, key, value, label):
        """Handle master slider changes"""
        if key in ['normal', 'midi']:
            label.setText(f"{value * 0.025:.2f}mm ({value})")
        elif key == 'midi_rapid_vel':
            label.setText(f"±{value}")
        else:
            label.setText(str(value))
        
        # If changing normal actuation and advanced is NOT shown, also update MIDI
        if key == 'normal' and not self.advanced_shown:
            self.master_widgets['midi_slider'].setValue(value)
            self.master_widgets['midi_label'].setText(f"{value * 0.025:.2f}mm ({value})")
        
        if not self.per_layer_enabled:
            for layer_data in self.layer_data:
                layer_data[key] = value
                # Also sync MIDI when changing normal without advanced shown
                if key == 'normal' and not self.advanced_shown:
                    layer_data['midi'] = value
    
    def on_master_combo_changed(self, key, combo):
        """Handle master combo changes"""
        if not self.per_layer_enabled:
            value = combo.currentData()
            for layer_data in self.layer_data:
                layer_data[key] = value
    
    def on_layer_slider_changed(self, key, value, label):
        """Handle layer slider changes"""
        if key in ['normal', 'midi']:
            label.setText(f"{value * 0.025:.2f}mm ({value})")
        elif key == 'midi_rapid_vel':
            label.setText(f"±{value}")
        else:
            label.setText(str(value))
        
        # If changing normal actuation and advanced is NOT shown, also update MIDI
        if key == 'normal' and not self.layer_widgets['advanced_checkbox'].isChecked():
            self.layer_widgets['midi_slider'].setValue(value)
            self.layer_widgets['midi_label'].setText(f"{value * 0.025:.2f}mm ({value})")
            self.layer_data[self.current_layer]['midi'] = value
        
        # Update layer data
        self.layer_data[self.current_layer][key] = value
    
    def on_layer_combo_changed(self, key, combo):
        """Handle layer combo changes"""
        self.layer_data[self.current_layer][key] = combo.currentData()
    
    def sync_all_to_master(self):
        """Sync all layer settings to master values"""
        master_data = {
            'normal': self.master_widgets['normal_slider'].value(),
            'midi': self.master_widgets['midi_slider'].value(),
            'aftertouch': self.master_widgets['aftertouch_combo'].currentData(),
            'velocity': self.master_widgets['velocity_combo'].currentData(),
            'rapid': self.master_widgets['rapid_slider'].value(),
            'midi_rapid_sens': self.master_widgets['midi_rapid_sens_slider'].value(),
            'midi_rapid_vel': self.master_widgets['midi_rapid_vel_slider'].value(),
            'vel_speed': self.master_widgets['vel_speed_combo'].currentData(),
            'aftertouch_cc': self.master_widgets['aftertouch_cc_combo'].currentData(),
            'rapidfire_enabled': self.master_widgets['rapid_checkbox'].isChecked(),
            'midi_rapidfire_enabled': self.master_widgets['midi_rapid_checkbox'].isChecked(),
            # HE Velocity settings
            'use_fixed_velocity': self.master_widgets['use_fixed_vel_checkbox'].isChecked(),
            'he_curve': self.master_widgets['he_curve_combo'].currentData(),
            'he_min': self.master_widgets['he_min_slider'].value(),
            'he_max': self.master_widgets['he_max_slider'].value()
        }

        for i in range(12):
            self.layer_data[i] = master_data.copy()
    
    def get_all_actuations(self):
        """Get all actuation values as a list of dicts"""
        actuations = []
        for layer_data in self.layer_data:
            # Build flags byte
            flags = 0
            if layer_data['rapidfire_enabled']:
                flags |= 0x01
            if layer_data['midi_rapidfire_enabled']:
                flags |= 0x02
            if layer_data['use_fixed_velocity']:
                flags |= 0x04

            data_dict = {
                'normal': layer_data['normal'],
                'midi': layer_data['midi'],
                'aftertouch': layer_data['aftertouch'],
                'velocity': layer_data['velocity'],
                'rapid': layer_data['rapid'],
                'midi_rapid_sens': layer_data['midi_rapid_sens'],
                'midi_rapid_vel': layer_data['midi_rapid_vel'],
                'vel_speed': layer_data['vel_speed'],
                'aftertouch_cc': layer_data['aftertouch_cc'],
                'flags': flags,
                # HE Velocity settings
                'he_curve': layer_data['he_curve'],
                'he_min': layer_data['he_min'],
                'he_max': layer_data['he_max']
            }
            actuations.append(data_dict)
        return actuations
    
    def on_save(self):
        """Save all actuation settings to keyboard"""
        try:
            # Save current layer UI to data before saving
            if self.per_layer_enabled:
                self.save_ui_to_layer(self.current_layer)
            
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")
            
            actuations = self.get_all_actuations()
            
            # Send all 12 layers (14 bytes each: layer + 10 original + 3 HE velocity)
            for layer, values in enumerate(actuations):
                data = bytearray([
                    layer,
                    values['normal'],
                    values['midi'],
                    values['aftertouch'],
                    values['velocity'],
                    values['rapid'],
                    values['midi_rapid_sens'],
                    values['midi_rapid_vel'],
                    values['vel_speed'],
                    values['aftertouch_cc'],
                    values['flags'],
                    # HE Velocity fields
                    values['he_curve'],
                    values['he_min'],
                    values['he_max']
                ])

                if not self.device.keyboard.set_layer_actuation(data):
                    raise RuntimeError(f"Failed to set actuation for layer {layer}")
            
            QMessageBox.information(None, "Success", 
                "Layer actuations saved successfully!")
                
        except Exception as e:
            QMessageBox.critical(None, "Error", 
                f"Failed to save actuations: {str(e)}")
    
    def on_load_from_keyboard(self):
        """Load all actuation settings from keyboard"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")
            
            # Get all actuations (156 bytes = 12 layers × 13 values)
            # 10 original + 3 HE velocity (flags, he_curve, he_min, he_max)
            actuations = self.device.keyboard.get_all_layer_actuations()

            if not actuations or len(actuations) != 156:
                raise RuntimeError("Failed to load actuations from keyboard")

            # Check if all layers are the same
            all_same = True
            first_values = {}

            for key_idx, key in enumerate(['normal', 'midi', 'aftertouch', 'velocity', 'rapid',
                                          'midi_rapid_sens', 'midi_rapid_vel', 'vel_speed',
                                          'aftertouch_cc', 'flags', 'he_curve', 'he_min', 'he_max']):
                first_values[key] = actuations[key_idx]

                for layer in range(1, 12):
                    offset = layer * 13 + key_idx
                    if actuations[offset] != first_values[key]:
                        all_same = False
                        break
                if not all_same:
                    break

            # Load into layer data
            for layer in range(12):
                offset = layer * 13
                flags = actuations[offset + 9]

                self.layer_data[layer] = {
                    'normal': actuations[offset + 0],
                    'midi': actuations[offset + 1],
                    'aftertouch': actuations[offset + 2],
                    'velocity': actuations[offset + 3],
                    'rapid': actuations[offset + 4],
                    'midi_rapid_sens': actuations[offset + 5],
                    'midi_rapid_vel': actuations[offset + 6],
                    'vel_speed': actuations[offset + 7],
                    'aftertouch_cc': actuations[offset + 8],
                    'rapidfire_enabled': (flags & 0x01) != 0,
                    'midi_rapidfire_enabled': (flags & 0x02) != 0,
                    'use_fixed_velocity': (flags & 0x04) != 0,
                    # HE Velocity fields
                    'he_curve': actuations[offset + 10],
                    'he_min': actuations[offset + 11],
                    'he_max': actuations[offset + 12]
                }
            
            # Set master controls
            self.master_widgets['normal_slider'].setValue(first_values['normal'])
            self.master_widgets['midi_slider'].setValue(first_values['midi'])
            
            for key in ['aftertouch', 'aftertouch_cc', 'velocity', 'vel_speed']:
                combo = self.master_widgets[f'{key}_combo']
                for i in range(combo.count()):
                    if combo.itemData(i) == first_values[key]:
                        combo.setCurrentIndex(i)
                        break
            
            # Rapidfire
            first_flags = first_values['flags']
            rapid_enabled = (first_flags & 0x01) != 0
            self.master_widgets['rapid_checkbox'].setChecked(rapid_enabled)
            self.master_widgets['rapid_widget'].setVisible(rapid_enabled)
            self.master_widgets['rapid_slider'].setValue(first_values['rapid'])
            
            # MIDI Rapidfire
            midi_rapid_enabled = (first_flags & 0x02) != 0
            self.master_widgets['midi_rapid_checkbox'].setChecked(midi_rapid_enabled)
            self.master_widgets['midi_rapid_sens_widget'].setVisible(midi_rapid_enabled)
            self.master_widgets['midi_rapid_vel_widget'].setVisible(midi_rapid_enabled)
            self.master_widgets['midi_rapid_sens_slider'].setValue(first_values['midi_rapid_sens'])
            self.master_widgets['midi_rapid_vel_slider'].setValue(first_values['midi_rapid_vel'])

            # HE Velocity settings
            use_fixed_vel = (first_flags & 0x04) != 0
            self.master_widgets['use_fixed_vel_checkbox'].setChecked(use_fixed_vel)
            self.master_widgets['he_min_slider'].setValue(first_values['he_min'])
            self.master_widgets['he_max_slider'].setValue(first_values['he_max'])

            # HE Velocity Curve combo
            he_curve_combo = self.master_widgets['he_curve_combo']
            for i in range(he_curve_combo.count()):
                if he_curve_combo.itemData(i) == first_values['he_curve']:
                    he_curve_combo.setCurrentIndex(i)
                    break

            # Load current layer to UI if in per-layer mode
            if self.per_layer_enabled:
                self.load_layer_to_ui(self.current_layer)
            
            self.per_layer_checkbox.setChecked(not all_same)
            
            QMessageBox.information(None, "Success", 
                "Layer actuations loaded successfully!")
                
        except Exception as e:
            QMessageBox.critical(None, "Error", 
                f"Failed to load actuations: {str(e)}")
    
    def on_reset(self):
        """Reset all actuations to defaults"""
        try:
            reply = QMessageBox.question(None, "Confirm Reset", 
                "Reset all layer actuations to defaults? This cannot be undone.",
                QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                if not self.device or not isinstance(self.device, VialKeyboard):
                    raise RuntimeError("Device not connected")
                
                if not self.device.keyboard.reset_layer_actuations():
                    raise RuntimeError("Failed to reset actuations")
                
                # Update UI to defaults
                defaults = {
                    'normal': 80,
                    'midi': 80,
                    'aftertouch': 0,
                    'velocity': 2,
                    'rapid': 4,
                    'midi_rapid_sens': 10,
                    'midi_rapid_vel': 10,
                    'vel_speed': 10,
                    'aftertouch_cc': 255,  # 255 = off (no CC sent)
                    'rapidfire_enabled': False,
                    'midi_rapidfire_enabled': False
                }
                
                # Reset master
                self.master_widgets['normal_slider'].setValue(defaults['normal'])
                self.master_widgets['midi_slider'].setValue(defaults['midi'])
                
                for key in ['aftertouch', 'aftertouch_cc', 'velocity', 'vel_speed']:
                    combo = self.master_widgets[f'{key}_combo']
                    for i in range(combo.count()):
                        if combo.itemData(i) == defaults[key]:
                            combo.setCurrentIndex(i)
                            break
                
                self.master_widgets['rapid_checkbox'].setChecked(False)
                self.master_widgets['rapid_widget'].setVisible(False)
                self.master_widgets['rapid_slider'].setValue(defaults['rapid'])
                
                self.master_widgets['midi_rapid_checkbox'].setChecked(False)
                self.master_widgets['midi_rapid_sens_widget'].setVisible(False)
                self.master_widgets['midi_rapid_vel_widget'].setVisible(False)
                self.master_widgets['midi_rapid_sens_slider'].setValue(defaults['midi_rapid_sens'])
                self.master_widgets['midi_rapid_vel_slider'].setValue(defaults['midi_rapid_vel'])
                
                # Reset all layer data
                for i in range(12):
                    self.layer_data[i] = defaults.copy()
                
                # Reload current layer to UI if in per-layer mode
                if self.per_layer_enabled:
                    self.load_layer_to_ui(self.current_layer)
                
                self.per_layer_checkbox.setChecked(False)
                
                QMessageBox.information(None, "Success", 
                    "Layer actuations reset to defaults!")
                    
        except Exception as e:
            QMessageBox.critical(None, "Error", 
                f"Failed to reset actuations: {str(e)}")
    
    def valid(self):
        return isinstance(self.device, VialKeyboard)

    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return

        # Load actuation settings from keyboard
        self.on_load_from_keyboard_silent()

    def on_load_from_keyboard_silent(self):
        """Load settings without showing success message"""
        if not self.device or not isinstance(self.device, VialKeyboard):
            return
        
        actuations = self.device.keyboard.get_all_layer_actuations()
        
        if not actuations or len(actuations) != 120:
            return
        
        # Parse and apply (same logic as on_load_from_keyboard but silent)
        all_same = True
        first_values = {}
        
        for key_idx, key in enumerate(['normal', 'midi', 'aftertouch', 'velocity', 'rapid', 
                                      'midi_rapid_sens', 'midi_rapid_vel', 'vel_speed', 
                                      'aftertouch_cc', 'flags']):
            first_values[key] = actuations[key_idx]
            
            for layer in range(1, 12):
                offset = layer * 10 + key_idx
                if actuations[offset] != first_values[key]:
                    all_same = False
                    break
            if not all_same:
                break
        
        for layer in range(12):
            offset = layer * 10
            flags = actuations[offset + 9]
            
            self.layer_data[layer] = {
                'normal': actuations[offset + 0],
                'midi': actuations[offset + 1],
                'aftertouch': actuations[offset + 2],
                'velocity': actuations[offset + 3],
                'rapid': actuations[offset + 4],
                'midi_rapid_sens': actuations[offset + 5],
                'midi_rapid_vel': actuations[offset + 6],
                'vel_speed': actuations[offset + 7],
                'aftertouch_cc': actuations[offset + 8],
                'rapidfire_enabled': (flags & 0x01) != 0,
                'midi_rapidfire_enabled': (flags & 0x02) != 0
            }
        
        self.master_widgets['normal_slider'].setValue(first_values['normal'])
        self.master_widgets['midi_slider'].setValue(first_values['midi'])
        
        for key in ['aftertouch', 'aftertouch_cc', 'velocity', 'vel_speed']:
            combo = self.master_widgets[f'{key}_combo']
            for i in range(combo.count()):
                if combo.itemData(i) == first_values[key]:
                    combo.setCurrentIndex(i)
                    break
        
        first_flags = first_values['flags']
        rapid_enabled = (first_flags & 0x01) != 0
        self.master_widgets['rapid_checkbox'].setChecked(rapid_enabled)
        self.master_widgets['rapid_widget'].setVisible(rapid_enabled)
        self.master_widgets['rapid_slider'].setValue(first_values['rapid'])
        
        midi_rapid_enabled = (first_flags & 0x02) != 0
        self.master_widgets['midi_rapid_checkbox'].setChecked(midi_rapid_enabled)
        self.master_widgets['midi_rapid_sens_widget'].setVisible(midi_rapid_enabled)
        self.master_widgets['midi_rapid_vel_widget'].setVisible(midi_rapid_enabled)
        self.master_widgets['midi_rapid_sens_slider'].setValue(first_values['midi_rapid_sens'])
        self.master_widgets['midi_rapid_vel_slider'].setValue(first_values['midi_rapid_vel'])
        
        if self.per_layer_enabled:
            self.load_layer_to_ui(self.current_layer)
        
        self.per_layer_checkbox.setChecked(not all_same)




class GamingConfigurator(BasicEditor):

    def __init__(self):
        super().__init__()
        self.keyboard = None
        self.gaming_controls = {}
        self.active_control_id = None  # Track which control is being assigned
        self.setup_ui()

    def setup_ui(self):
        # Create scroll area for better window resizing
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        scroll_area.setWidget(main_widget)
        self.addWidget(scroll_area)

        # Create horizontal layout for calibration (left) and gamepad (center)
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(30)
        main_layout.addLayout(controls_layout)

        # Add outer stretch to center content
        controls_layout.addStretch(1)

        # Analog Calibration Group (LEFT SIDE)
        calibration_group = QGroupBox(tr("GamingConfigurator", "Analog Calibration"))
        calibration_group.setMaximumWidth(250)
        calibration_layout = QVBoxLayout()
        calibration_layout.setSpacing(8)
        calibration_group.setLayout(calibration_layout)
        controls_layout.addWidget(calibration_group, alignment=QtCore.Qt.AlignTop)

        # Helper function to create compact slider
        def create_compact_slider(label_text, default_value):
            widget = QWidget()
            layout = QVBoxLayout()
            layout.setSpacing(2)
            layout.setContentsMargins(0, 0, 0, 0)
            widget.setLayout(layout)

            label_with_value = QLabel(f"{label_text}: {default_value/10:.1f}")
            layout.addWidget(label_with_value)

            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(25)
            slider.setValue(default_value)
            slider.setTickInterval(1)
            slider.setMinimumWidth(200)
            layout.addWidget(slider)

            slider.valueChanged.connect(
                lambda val, lbl=label_with_value, txt=label_text: lbl.setText(f"{txt}: {val/10:.1f}")
            )

            return widget, slider, label_with_value

        # LS (Left Stick) Calibration
        ls_label = QLabel("<b>Left Stick</b>")
        calibration_layout.addWidget(ls_label)

        ls_min_widget, self.ls_min_travel_slider, self.ls_min_travel_label = create_compact_slider(
            tr("GamingConfigurator", "Min Travel (mm)"), 10
        )
        calibration_layout.addWidget(ls_min_widget)

        ls_max_widget, self.ls_max_travel_slider, self.ls_max_travel_label = create_compact_slider(
            tr("GamingConfigurator", "Max Travel (mm)"), 20
        )
        calibration_layout.addWidget(ls_max_widget)

        # RS (Right Stick) Calibration
        rs_label = QLabel("<b>Right Stick</b>")
        calibration_layout.addWidget(rs_label)

        rs_min_widget, self.rs_min_travel_slider, self.rs_min_travel_label = create_compact_slider(
            tr("GamingConfigurator", "Min Travel (mm)"), 10
        )
        calibration_layout.addWidget(rs_min_widget)

        rs_max_widget, self.rs_max_travel_slider, self.rs_max_travel_label = create_compact_slider(
            tr("GamingConfigurator", "Max Travel (mm)"), 20
        )
        calibration_layout.addWidget(rs_max_widget)

        # Triggers Calibration
        trigger_label = QLabel("<b>Triggers</b>")
        calibration_layout.addWidget(trigger_label)

        trigger_min_widget, self.trigger_min_travel_slider, self.trigger_min_travel_label = create_compact_slider(
            tr("GamingConfigurator", "Min Travel (mm)"), 10
        )
        calibration_layout.addWidget(trigger_min_widget)

        trigger_max_widget, self.trigger_max_travel_slider, self.trigger_max_travel_label = create_compact_slider(
            tr("GamingConfigurator", "Max Travel (mm)"), 20
        )
        calibration_layout.addWidget(trigger_max_widget)

        # MIDDLE COLUMN: Curve Editor and Gamepad Response
        middle_column = QWidget()
        middle_layout = QVBoxLayout()
        middle_layout.setSpacing(15)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_column.setLayout(middle_layout)

        # Analog Curve Section
        from widgets.curve_editor import CurveEditorWidget
        curve_group = QGroupBox(tr("GamingConfigurator", "Analog Curve"))
        curve_group.setMaximumWidth(350)
        curve_group_layout = QVBoxLayout()
        curve_group.setLayout(curve_group_layout)

        self.curve_editor = CurveEditorWidget(show_save_button=True)
        self.curve_editor.curve_changed.connect(self.on_curve_changed)
        self.curve_editor.save_to_user_requested.connect(self.on_save_curve_to_user)
        self.curve_editor.user_curve_selected.connect(self.on_user_curve_selected)
        curve_group_layout.addWidget(self.curve_editor)

        middle_layout.addWidget(curve_group)

        # Gamepad Response Section
        response_group = QGroupBox(tr("GamingConfigurator", "Gamepad Response"))
        response_group.setMaximumWidth(350)
        response_layout = QVBoxLayout()
        response_group.setLayout(response_layout)

        # Angle Adjustment
        self.angle_adj_checkbox = QCheckBox(tr("GamingConfigurator", "Enable angle adjustment"))
        response_layout.addWidget(self.angle_adj_checkbox)

        # Diagonal Angle Slider
        angle_widget = QWidget()
        angle_layout = QVBoxLayout()
        angle_layout.setSpacing(2)
        angle_layout.setContentsMargins(20, 0, 0, 0)  # Indent
        angle_widget.setLayout(angle_layout)

        self.diagonal_angle_label = QLabel("Diagonal Angle: 0°")
        angle_layout.addWidget(self.diagonal_angle_label)

        self.diagonal_angle_slider = QSlider(Qt.Horizontal)
        self.diagonal_angle_slider.setMinimum(0)
        self.diagonal_angle_slider.setMaximum(90)
        self.diagonal_angle_slider.setValue(0)
        self.diagonal_angle_slider.setTickInterval(10)
        self.diagonal_angle_slider.valueChanged.connect(
            lambda val: self.diagonal_angle_label.setText(f"Diagonal Angle: {val}°")
        )
        angle_layout.addWidget(self.diagonal_angle_slider)

        response_layout.addWidget(angle_widget)

        # Square Output
        self.square_output_checkbox = QCheckBox(tr("GamingConfigurator", "Use Square joystick output"))
        self.square_output_checkbox.setToolTip(tr("GamingConfigurator",
            "Restrict joystick movement to a square instead of circle.\n"
            "Allows maximum axis output. Recommended for Rocket League and CS:GO."))
        response_layout.addWidget(self.square_output_checkbox)

        # Snappy Joystick
        self.snappy_joystick_checkbox = QCheckBox(tr("GamingConfigurator", "Snappy Joystick"))
        self.snappy_joystick_checkbox.setToolTip(tr("GamingConfigurator",
            "Use maximum value of opposite sides of axis rather than combining them."))
        response_layout.addWidget(self.snappy_joystick_checkbox)

        middle_layout.addWidget(response_group)
        middle_layout.addStretch()

        controls_layout.addWidget(middle_column, alignment=QtCore.Qt.AlignTop)

        # Create gamepad widget with drawn outline
        gamepad_widget = GamepadWidget()
        gamepad_widget.setFixedSize(750, 560)
        controls_layout.addWidget(gamepad_widget)

        # Map control IDs to positions and names (matching the original control IDs)
        control_mapping = {
            # D-pad
            10: ("D-pad Up", "dpad_up", 180, 105, 56, 58, "↑"),
            11: ("D-pad Down", "dpad_down", 180, 163, 56, 58, "↓"),
            12: ("D-pad Left", "dpad_left", 150, 135, 58, 56, "←"),
            13: ("D-pad Right", "dpad_right", 208, 135, 58, 56, "→"),
            # Face buttons
            14: ("Button 1", "btn1", 517, 178, 50, 50, "1"),  # A
            15: ("Button 2", "btn2", 553, 139, 50, 50, "2"),  # B
            16: ("Button 3", "btn3", 481, 139, 50, 50, "3"),  # X
            17: ("Button 4", "btn4", 517, 103, 50, 50, "4"),  # Y
            # Sticks
            0: ("LS Up", "ls_up", 275, 185, 38, 38, "↑"),
            1: ("LS Down", "ls_down", 275, 261, 38, 38, "↓"),
            2: ("LS Left", "ls_left", 237, 223, 38, 38, "←"),
            3: ("LS Right", "ls_right", 313, 223, 38, 38, "→"),
            22: ("LS Click", "l3", 275, 223, 38, 38, "L3"),
            4: ("RS Up", "rs_up", 439, 185, 38, 38, "↑"),
            5: ("RS Down", "rs_down", 439, 261, 38, 38, "↓"),
            6: ("RS Left", "rs_left", 401, 223, 38, 38, "←"),
            7: ("RS Right", "rs_right", 477, 223, 38, 38, "→"),
            23: ("RS Click", "r3", 439, 223, 38, 38, "R3"),
            # Bumpers and triggers
            18: ("LB", "lb", 177, 65, 60, 30, "LB"),
            19: ("RB", "rb", 503, 65, 60, 30, "RB"),
            8: ("LT", "lt", 177, 25, 60, 35, "LT"),
            9: ("RT", "rt", 503, 25, 60, 35, "RT"),
            # Center buttons
            20: ("Back", "back", 320, 170, 50, 30, "Back"),
            21: ("Start", "start", 380, 170, 50, 30, "Start"),
        }

        # Create buttons positioned over gamepad
        for control_id, (name, key, x, y, w, h, text) in control_mapping.items():
            # Create button based on type
            if "dpad" in key:
                # Use DpadButton for d-pad with shaped paths
                btn = DpadButton("Not Set")
                btn.setFixedSize(w, h)
                btn.setParent(gamepad_widget)
                btn.move(x, y)

                # Set shaped path for d-pad buttons
                path = QPainterPath()
                if key == "dpad_up":
                    path.moveTo(28, 58)
                    path.lineTo(3, 33)
                    path.lineTo(3, 8)
                    path.quadTo(8, 3, 15, 3)
                    path.lineTo(41, 3)
                    path.quadTo(48, 3, 53, 8)
                    path.lineTo(53, 33)
                    path.lineTo(28, 58)
                    path.closeSubpath()
                elif key == "dpad_down":
                    path.moveTo(28, 0)
                    path.lineTo(3, 25)
                    path.lineTo(3, 50)
                    path.quadTo(8, 55, 15, 55)
                    path.lineTo(41, 55)
                    path.quadTo(48, 55, 53, 50)
                    path.lineTo(53, 25)
                    path.lineTo(28, 0)
                    path.closeSubpath()
                elif key == "dpad_left":
                    path.moveTo(58, 28)
                    path.lineTo(33, 3)
                    path.lineTo(8, 3)
                    path.quadTo(3, 8, 3, 15)
                    path.lineTo(3, 41)
                    path.quadTo(3, 48, 8, 53)
                    path.lineTo(33, 53)
                    path.lineTo(58, 28)
                    path.closeSubpath()
                elif key == "dpad_right":
                    path.moveTo(0, 28)
                    path.lineTo(25, 3)
                    path.lineTo(50, 3)
                    path.quadTo(55, 8, 55, 15)
                    path.lineTo(55, 41)
                    path.quadTo(55, 48, 50, 53)
                    path.lineTo(25, 53)
                    path.lineTo(0, 28)
                    path.closeSubpath()

                btn.setMask(QRegion(path.toFillPolygon().toPolygon()))
                btn.set_border_path(path)
            elif "btn" in key and key in ["btn1", "btn2", "btn3", "btn4"]:
                # Circular face buttons (exactly like GamingTab)
                btn = QPushButton("Not Set")
                btn.setFixedSize(w, h)
                btn.setParent(gamepad_widget)
                btn.move(x, y)
                btn.setStyleSheet("border-radius: 25px;")
            else:
                # Regular rectangular buttons (no special styling, exactly like GamingTab)
                btn = QPushButton("Not Set")
                btn.setFixedSize(w, h)
                btn.setParent(gamepad_widget)
                btn.move(x, y)

            btn.clicked.connect(lambda checked, cid=control_id: self.on_assign_key(cid))
            btn.setProperty("control_id", control_id)

            # Store reference with button type
            button_type = "dpad" if "dpad" in key else ("face" if key in ["btn1", "btn2", "btn3", "btn4"] else "regular")
            self.gaming_controls[control_id] = {
                'button': btn,
                'button_type': button_type,
                'keycode': None,
                'row': None,
                'col': None,
                'enabled': False
            }

        # Add outer stretch on the right
        controls_layout.addStretch(1)

        # Buttons
        main_layout.addStretch()
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        # Button style
        button_style = "QPushButton { border-radius: 3px; padding: 8px 16px; }"

        save_btn = QPushButton(tr("GamingConfigurator", "Save Configuration"))
        save_btn.setMinimumHeight(45)
        save_btn.setMinimumWidth(200)
        save_btn.setStyleSheet(button_style)
        save_btn.clicked.connect(self.on_save)
        buttons_layout.addWidget(save_btn)

        load_btn = QPushButton(tr("GamingConfigurator", "Load from Keyboard"))
        load_btn.setMinimumHeight(45)
        load_btn.setMinimumWidth(210)
        load_btn.setStyleSheet(button_style)
        load_btn.clicked.connect(self.on_load_from_keyboard)
        buttons_layout.addWidget(load_btn)

        reset_btn = QPushButton(tr("GamingConfigurator", "Reset to Defaults"))
        reset_btn.setMinimumHeight(45)
        reset_btn.setMinimumWidth(180)
        reset_btn.setStyleSheet(button_style)
        reset_btn.clicked.connect(self.on_reset)
        buttons_layout.addWidget(reset_btn)

        main_layout.addLayout(buttons_layout)

        # Add TabbedKeycodes at the bottom like in Macros tab
        from tabbed_keycodes import TabbedKeycodes
        self.tabbed_keycodes = TabbedKeycodes()
        self.tabbed_keycodes.keycode_changed.connect(self.on_keycode_selected)
        self.addWidget(self.tabbed_keycodes)

        # Apply stylesheet
        main_widget.setStyleSheet("""
            QCheckBox:focus {
                font-weight: normal;
                outline: none;
            }
            QPushButton:focus {
                font-weight: normal;
                outline: none;
            }
        """)

    def get_button_style(self, button_type, highlighted=False):
        """Get the appropriate style for a button based on its type"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QPalette

        if button_type == "face":
            # Face buttons are circular
            base_style = "border-radius: 25px;"
        elif button_type == "dpad":
            # D-pad buttons don't have inline styles (they use masks)
            base_style = ""
        else:
            # Regular buttons have no special styling
            base_style = ""

        if highlighted:
            # Use theme colors for highlighting
            palette = QApplication.palette()
            highlight_color = palette.color(QPalette.Highlight).name()
            highlight_text = palette.color(QPalette.HighlightedText).name()
            return f"QPushButton {{ {base_style} background-color: {highlight_color}; color: {highlight_text}; }}"
        else:
            # Return empty stylesheet to clear any previous styling (except base_style)
            return f"QPushButton {{ {base_style} }}"

    def on_assign_key(self, control_id):
        """Handle key assignment for a gaming control"""
        self.active_control_id = control_id
        # Highlight the button being assigned and unhighlight all others
        for cid, data in self.gaming_controls.items():
            button_type = data.get('button_type', 'regular')
            if cid == control_id:
                data['button'].setStyleSheet(self.get_button_style(button_type, highlighted=True))
            else:
                # Always set style to clear any previous highlighting
                data['button'].setStyleSheet(self.get_button_style(button_type, highlighted=False))

    def on_keycode_selected(self, keycode):
        """Called when a keycode is selected from TabbedKeycodes"""
        if self.active_control_id is None or not self.keyboard:
            return

        # Find the physical position (row, col) of this keycode - search ALL layers
        row, col = self.find_keycode_position(keycode)

        if row is not None and col is not None:
            # Assign to the active control
            data = self.gaming_controls[self.active_control_id]
            data['keycode'] = keycode
            data['row'] = row
            data['col'] = col
            data['enabled'] = True

            # Update button text to show the keycode label
            from keycodes.keycodes import Keycode
            label = Keycode.label(keycode)
            # Truncate label to fit in 50x50 button
            if len(label) > 7:
                label = label[:6] + ".."
            data['button'].setText(label)

            # Reset button style based on its type (clears highlighting)
            button_type = data.get('button_type', 'regular')
            data['button'].setStyleSheet(self.get_button_style(button_type, highlighted=False))

            # Clear active control
            self.active_control_id = None
        else:
            # Keycode not found in any layer - show error
            QMessageBox.warning(None, "Key Not Found",
                              f"The selected keycode is not found in your keymap on any layer.\n"
                              f"Please select a key that exists in your keymap.")
            # Reset the button style (clears highlighting)
            data = self.gaming_controls[self.active_control_id]
            button_type = data.get('button_type', 'regular')
            data['button'].setStyleSheet(self.get_button_style(button_type, highlighted=False))
            self.active_control_id = None

    def find_keycode_position(self, keycode):
        """Find the matrix position (row, col) of a keycode - searches ALL layers"""
        if not self.keyboard:
            return None, None

        # Search through ALL layers for this keycode (prefer layer 0 first)
        for (layer, row, col), kc in sorted(self.keyboard.layout.items()):
            if kc == keycode:
                return row, col

        return None, None

    def on_save(self):
        """Save gaming configuration to keyboard"""
        if not self.keyboard:
            QMessageBox.warning(None, "No Keyboard", "No keyboard connected")
            return

        try:
            # Save analog configuration - separate for LS, RS, and Triggers
            ls_min = self.ls_min_travel_slider.value()
            ls_max = self.ls_max_travel_slider.value()
            rs_min = self.rs_min_travel_slider.value()
            rs_max = self.rs_max_travel_slider.value()
            trigger_min = self.trigger_min_travel_slider.value()
            trigger_max = self.trigger_max_travel_slider.value()

            # Validate ranges
            if ls_min >= ls_max:
                QMessageBox.warning(None, "Invalid Range", "LS Min travel must be less than LS Max travel")
                return
            if rs_min >= rs_max:
                QMessageBox.warning(None, "Invalid Range", "RS Min travel must be less than RS Max travel")
                return
            if trigger_min >= trigger_max:
                QMessageBox.warning(None, "Invalid Range", "Trigger Min travel must be less than Trigger Max travel")
                return

            success = self.keyboard.set_gaming_analog_config(ls_min, ls_max, rs_min, rs_max, trigger_min, trigger_max)

            # Save key mappings
            for control_id, data in self.gaming_controls.items():
                if data['enabled'] and data['row'] is not None and data['col'] is not None:
                    self.keyboard.set_gaming_key_map(control_id, data['row'], data['col'], 1)
                else:
                    self.keyboard.set_gaming_key_map(control_id, 0, 0, 0)

            # Save gamepad response settings
            angle_adj_enabled = self.angle_adj_checkbox.isChecked()
            diagonal_angle = self.diagonal_angle_slider.value()
            square_output = self.square_output_checkbox.isChecked()
            snappy_joystick = self.snappy_joystick_checkbox.isChecked()

            # Get current curve index from preset combo
            current_curve_index = self.curve_editor.preset_combo.currentData()
            if current_curve_index is None or current_curve_index < 0:
                current_curve_index = 0  # Default to linear

            response_success = self.keyboard.set_gaming_response(
                angle_adj_enabled, diagonal_angle, square_output, snappy_joystick, current_curve_index
            )

            if success and response_success:
                QMessageBox.information(None, "Success", "Gaming configuration saved successfully")
            else:
                QMessageBox.warning(None, "Error", "Failed to save gaming configuration")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error saving configuration: {str(e)}")

    def on_load_from_keyboard(self):
        """Load gaming configuration from keyboard"""
        if not self.keyboard:
            QMessageBox.warning(None, "No Keyboard", "No keyboard connected")
            return

        try:
            settings = self.keyboard.get_gaming_settings()
            if settings:
                # Block signals while updating
                self.ls_min_travel_slider.blockSignals(True)
                self.ls_max_travel_slider.blockSignals(True)
                self.rs_min_travel_slider.blockSignals(True)
                self.rs_max_travel_slider.blockSignals(True)
                self.trigger_min_travel_slider.blockSignals(True)
                self.trigger_max_travel_slider.blockSignals(True)

                # Set values for LS/RS/Triggers
                self.ls_min_travel_slider.setValue(settings.get('ls_min_travel_mm_x10', 10))
                self.ls_max_travel_slider.setValue(settings.get('ls_max_travel_mm_x10', 20))
                self.rs_min_travel_slider.setValue(settings.get('rs_min_travel_mm_x10', 10))
                self.rs_max_travel_slider.setValue(settings.get('rs_max_travel_mm_x10', 20))
                self.trigger_min_travel_slider.setValue(settings.get('trigger_min_travel_mm_x10', 10))
                self.trigger_max_travel_slider.setValue(settings.get('trigger_max_travel_mm_x10', 20))

                self.ls_min_travel_slider.blockSignals(False)
                self.ls_max_travel_slider.blockSignals(False)
                self.rs_min_travel_slider.blockSignals(False)
                self.rs_max_travel_slider.blockSignals(False)
                self.trigger_min_travel_slider.blockSignals(False)
                self.trigger_max_travel_slider.blockSignals(False)

                # Update labels (with inline format)
                self.ls_min_travel_label.setText(f"Min Travel (mm): {settings.get('ls_min_travel_mm_x10', 10)/10:.1f}")
                self.ls_max_travel_label.setText(f"Max Travel (mm): {settings.get('ls_max_travel_mm_x10', 20)/10:.1f}")
                self.rs_min_travel_label.setText(f"Min Travel (mm): {settings.get('rs_min_travel_mm_x10', 10)/10:.1f}")
                self.rs_max_travel_label.setText(f"Max Travel (mm): {settings.get('rs_max_travel_mm_x10', 20)/10:.1f}")
                self.trigger_min_travel_label.setText(f"Min Travel (mm): {settings.get('trigger_min_travel_mm_x10', 10)/10:.1f}")
                self.trigger_max_travel_label.setText(f"Max Travel (mm): {settings.get('trigger_max_travel_mm_x10', 20)/10:.1f}")

                # Load user curve names first (so dropdown is populated)
                user_curve_names = self.keyboard.get_all_user_curve_names()
                if user_curve_names and len(user_curve_names) == 10:
                    self.curve_editor.set_user_curve_names(user_curve_names)

                # Load gamepad response settings
                response = self.keyboard.get_gaming_response()
                if response:
                    self.angle_adj_checkbox.setChecked(response.get('angle_adj_enabled', False))
                    self.diagonal_angle_slider.setValue(response.get('diagonal_angle', 0))
                    self.diagonal_angle_label.setText(f"Diagonal Angle: {response.get('diagonal_angle', 0)}°")
                    self.square_output_checkbox.setChecked(response.get('square_output', False))
                    self.snappy_joystick_checkbox.setChecked(response.get('snappy_joystick', False))

                    # Select curve in combo box
                    curve_index = response.get('curve_index', 0)
                    self.curve_editor.select_curve(curve_index)

                    # If it's a user curve (7-16), load the actual points
                    if curve_index >= 7 and curve_index <= 16:
                        slot_index = curve_index - 7
                        curve_data = self.keyboard.get_user_curve(slot_index)
                        if curve_data and 'points' in curve_data:
                            self.curve_editor.load_user_curve_points(curve_data['points'])

                QMessageBox.information(None, "Success", "Gaming configuration loaded from keyboard")
            else:
                QMessageBox.warning(None, "Error", "Failed to load gaming configuration")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error loading configuration: {str(e)}")

    def on_reset(self):
        """Reset gaming configuration to defaults"""
        if not self.keyboard:
            QMessageBox.warning(None, "No Keyboard", "No keyboard connected")
            return

        reply = QMessageBox.question(None, "Confirm Reset",
                                     "Reset gaming configuration to defaults?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                success = self.keyboard.reset_gaming_settings()
                if success:
                    self.on_load_from_keyboard()
                    # Clear all assignments
                    for data in self.gaming_controls.values():
                        data['button'].setText("Not Set")
                        data['button'].setStyleSheet("QPushButton { text-align: center; border-radius: 3px; font-size: 9px; }")
                        data['keycode'] = None
                        data['row'] = None
                        data['col'] = None
                        data['enabled'] = False
                    QMessageBox.information(None, "Success", "Gaming configuration reset to defaults")
                else:
                    QMessageBox.warning(None, "Error", "Failed to reset gaming configuration")
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Error resetting configuration: {str(e)}")

    def on_curve_changed(self, points):
        """Called when curve points are changed - IMMEDIATE SAVE for analog curves"""
        if not self.keyboard:
            return

        # Get curve index from preset combo (0-16 or -1 for custom)
        curve_index = self.curve_editor.get_selected_curve_index()
        if curve_index is None or curve_index < 0:
            # Custom curve - user needs to save to a user slot first
            return

        try:
            # Get current response settings and update with new curve index
            response = self.keyboard.get_gaming_response()
            if response:
                self.keyboard.set_gaming_response(
                    response['angle_adj_enabled'],
                    response['diagonal_angle'],
                    response['square_output'],
                    response['snappy_joystick'],
                    curve_index
                )
        except Exception as e:
            print(f"Error saving analog curve: {e}")

    def on_user_curve_selected(self, slot_index):
        """Handle user curve selection - load curve points from keyboard and save immediately"""
        if not self.keyboard:
            return

        try:
            # Fetch user curve from keyboard
            curve_data = self.keyboard.get_user_curve(slot_index)
            if curve_data and 'points' in curve_data:
                # Load points into editor and cache for later (pass slot_index for caching)
                self.curve_editor.load_user_curve_points(curve_data['points'], slot_index)

                # Save with the correct curve index (7 + slot_index)
                curve_index = 7 + slot_index
                response = self.keyboard.get_gaming_response()
                if response:
                    self.keyboard.set_gaming_response(
                        response['angle_adj_enabled'],
                        response['diagonal_angle'],
                        response['square_output'],
                        response['snappy_joystick'],
                        curve_index
                    )
        except Exception as e:
            print(f"Error loading user curve: {e}")

    def on_save_curve_to_user(self, slot_index, curve_name):
        """Called when user wants to save current curve to a user slot"""
        if not self.keyboard:
            QMessageBox.warning(None, "No Keyboard", "No keyboard connected")
            return

        try:
            # Get current curve points
            points = self.curve_editor.get_points()

            # Save to keyboard
            success = self.keyboard.set_user_curve(slot_index, points, curve_name)

            if success:
                QMessageBox.information(None, "Success",
                                      f"Curve saved to {curve_name}")

                # Reload user curve names to show the updated name
                user_curve_names = self.keyboard.get_all_user_curve_names()
                if user_curve_names and len(user_curve_names) == 10:
                    self.curve_editor.set_user_curve_names(user_curve_names)

                # Select the newly saved curve (curve index = 7 + slot_index)
                self.curve_editor.select_curve(7 + slot_index)

                # Immediately save to gaming response
                curve_index = 7 + slot_index
                response = self.keyboard.get_gaming_response()
                if response:
                    self.keyboard.set_gaming_response(
                        response['angle_adj_enabled'],
                        response['diagonal_angle'],
                        response['square_output'],
                        response['snappy_joystick'],
                        curve_index
                    )
            else:
                QMessageBox.warning(None, "Error", "Failed to save curve")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error saving curve: {str(e)}")

    def rebuild(self, device):
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard
            # Set keyboard reference for tabbed keycodes (so GamingTab can access it)
            self.tabbed_keycodes.set_keyboard(self.keyboard)
            self.tabbed_keycodes.recreate_keycode_buttons()
            # Try to load settings silently without showing message boxes
            try:
                # Use cached gaming settings if available, otherwise fetch them
                settings = getattr(self.keyboard, 'gaming_settings', None) or self.keyboard.get_gaming_settings()
                if settings:
                    # Block signals while updating
                    self.ls_min_travel_slider.blockSignals(True)
                    self.ls_max_travel_slider.blockSignals(True)
                    self.rs_min_travel_slider.blockSignals(True)
                    self.rs_max_travel_slider.blockSignals(True)
                    self.trigger_min_travel_slider.blockSignals(True)
                    self.trigger_max_travel_slider.blockSignals(True)

                    self.ls_min_travel_slider.setValue(settings.get('ls_min_travel_mm_x10', 10))
                    self.ls_max_travel_slider.setValue(settings.get('ls_max_travel_mm_x10', 20))
                    self.rs_min_travel_slider.setValue(settings.get('rs_min_travel_mm_x10', 10))
                    self.rs_max_travel_slider.setValue(settings.get('rs_max_travel_mm_x10', 20))
                    self.trigger_min_travel_slider.setValue(settings.get('trigger_min_travel_mm_x10', 10))
                    self.trigger_max_travel_slider.setValue(settings.get('trigger_max_travel_mm_x10', 20))

                    self.ls_min_travel_slider.blockSignals(False)
                    self.ls_max_travel_slider.blockSignals(False)
                    self.rs_min_travel_slider.blockSignals(False)
                    self.rs_max_travel_slider.blockSignals(False)
                    self.trigger_min_travel_slider.blockSignals(False)
                    self.trigger_max_travel_slider.blockSignals(False)

                    # Update labels (with inline format)
                    self.ls_min_travel_label.setText(f"Min Travel (mm): {settings.get('ls_min_travel_mm_x10', 10)/10:.1f}")
                    self.ls_max_travel_label.setText(f"Max Travel (mm): {settings.get('ls_max_travel_mm_x10', 20)/10:.1f}")
                    self.rs_min_travel_label.setText(f"Min Travel (mm): {settings.get('rs_min_travel_mm_x10', 10)/10:.1f}")
                    self.rs_max_travel_label.setText(f"Max Travel (mm): {settings.get('rs_max_travel_mm_x10', 20)/10:.1f}")
                    self.trigger_min_travel_label.setText(f"Min Travel (mm): {settings.get('trigger_min_travel_mm_x10', 10)/10:.1f}")
                    self.trigger_max_travel_label.setText(f"Max Travel (mm): {settings.get('trigger_max_travel_mm_x10', 20)/10:.1f}")

                # Load user curve names (so dropdown is populated)
                user_curve_names = self.keyboard.get_all_user_curve_names()
                if user_curve_names and len(user_curve_names) == 10:
                    self.curve_editor.set_user_curve_names(user_curve_names)

                # Load gamepad response settings including curve
                response = self.keyboard.get_gaming_response()
                if response:
                    self.angle_adj_checkbox.blockSignals(True)
                    self.diagonal_angle_slider.blockSignals(True)
                    self.square_output_checkbox.blockSignals(True)
                    self.snappy_joystick_checkbox.blockSignals(True)

                    self.angle_adj_checkbox.setChecked(response.get('angle_adj_enabled', False))
                    self.diagonal_angle_slider.setValue(response.get('diagonal_angle', 0))
                    self.diagonal_angle_label.setText(f"Diagonal Angle: {response.get('diagonal_angle', 0)}°")
                    self.square_output_checkbox.setChecked(response.get('square_output', False))
                    self.snappy_joystick_checkbox.setChecked(response.get('snappy_joystick', False))

                    self.angle_adj_checkbox.blockSignals(False)
                    self.diagonal_angle_slider.blockSignals(False)
                    self.square_output_checkbox.blockSignals(False)
                    self.snappy_joystick_checkbox.blockSignals(False)

                    # Select curve in combo box
                    curve_index = response.get('curve_index', 0)
                    self.curve_editor.select_curve(curve_index)

                    # If it's a user curve (7-16), load the actual points
                    if curve_index >= 7 and curve_index <= 16:
                        slot_index = curve_index - 7
                        curve_data = self.keyboard.get_user_curve(slot_index)
                        if curve_data and 'points' in curve_data:
                            self.curve_editor.load_user_curve_points(curve_data['points'])
            except:
                # Silently fail during rebuild - user can manually load if needed
                pass

    def valid(self):
        return isinstance(self.device, VialKeyboard)

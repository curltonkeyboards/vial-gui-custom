# SPDX-License-Identifier: GPL-2.0-or-later
import math
import struct
import json

from PyQt5.QtWidgets import (QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QLabel, 
                           QSizePolicy, QGroupBox, QGridLayout, QComboBox, QCheckBox, 
                           QTableWidget, QHeaderView, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5 import QtCore

from editor.basic_editor import BasicEditor
from protocol.constants import VIAL_PROTOCOL_MATRIX_TESTER
from widgets.keyboard_widget import KeyboardWidget2
from util import tr
from vial_device import VialKeyboard
from unlocker import Unlocker


class MatrixTest(BasicEditor):

    def __init__(self, layout_editor):
        super().__init__()

        self.layout_editor = layout_editor

        self.KeyboardWidget2 = KeyboardWidget2(layout_editor)
        self.KeyboardWidget2.set_enabled(False)

        self.unlock_btn = QPushButton("Unlock")
        self.reset_btn = QPushButton("Reset")

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
        self.addStretch()
        
        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        main_widget.setMinimumWidth(1000)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.addWidget(main_widget)
        self.setAlignment(main_widget, QtCore.Qt.AlignHCenter)
        
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
        self.loop_channel = QComboBox()
        self.loop_channel.setMinimumWidth(150)
        self.loop_channel.setMaximumHeight(25)
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
        
        # Main Functions Table (bigger to prevent cutoff)
        self.main_group = QGroupBox(tr("ThruLoopConfigurator", "Main Functions"))
        main_layout.addWidget(self.main_group)
        self.main_table = self.create_main_function_table()
        main_group_layout = QVBoxLayout()
        main_group_layout.addWidget(self.main_table)
        self.main_group.setLayout(main_group_layout)
        
        # Overdub Functions Table  
        self.overdub_group = QGroupBox(tr("ThruLoopConfigurator", "Overdub Functions"))
        main_layout.addWidget(self.overdub_group)
        self.overdub_table = self.create_function_table()
        overdub_group_layout = QVBoxLayout()
        overdub_group_layout.addWidget(self.overdub_table)
        self.overdub_group.setLayout(overdub_group_layout)
        
        # Buttons
        self.addStretch()
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        save_btn = QPushButton(tr("ThruLoopConfigurator", "Save Configuration"))
        save_btn.clicked.connect(self.on_save)
        buttons_layout.addWidget(save_btn)
        
        load_btn = QPushButton(tr("ThruLoopConfigurator", "Load from Keyboard"))  
        load_btn.clicked.connect(self.on_load_from_keyboard)
        buttons_layout.addWidget(load_btn)
        
        reset_btn = QPushButton(tr("ThruLoopConfigurator", "Reset to Defaults"))
        reset_btn.clicked.connect(self.on_reset)
        buttons_layout.addWidget(reset_btn)
        
        self.addLayout(buttons_layout)
        
        # Apply stylesheet to prevent bold focus styling
        main_widget.setStyleSheet("""
            QCheckBox:focus {
                font-weight: normal;
                outline: none;
            }
            QPushButton:focus {
                font-weight: normal;
                outline: none;
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
    
    def create_cc_combo(self):
        """Create a CC selector combobox"""
        combo = QComboBox()
        combo.setMinimumWidth(120)
        combo.setMaximumHeight(25)
        
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
    
    def create_function_table(self):
        table = QTableWidget(6, 4)  # Changed from 5 to 6 rows
        table.setHorizontalHeaderLabels([f"Loop {i+1}" for i in range(4)])
        table.setVerticalHeaderLabels([
            "Start Recording", "Stop Recording", "Start Playing", "Stop Playing", "Clear", "Restart"  # Added "Restart"
        ])
        
        # Fill table with CC combos
        for row in range(6):  # Changed from 5 to 6
            for col in range(4):
                cc_combo = self.create_cc_combo()
                table.setCellWidget(row, col, cc_combo)
        
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setMaximumHeight(280)  # Increased from 200 to match main table
        table.setMinimumWidth(600)
        table.resizeRowsToContents()
        return table
    
    def create_main_function_table(self):
        table = QTableWidget(6, 4)
        table.setHorizontalHeaderLabels([f"Loop {i+1}" for i in range(4)])
        table.setVerticalHeaderLabels([
            "Start Recording", "Stop Recording", "Start Playing", "Stop Playing", "Clear", "Restart"
        ])
        
        # Fill table with CC combos
        for row in range(6):
            for col in range(4):
                cc_combo = self.create_cc_combo()
                table.setCellWidget(row, col, cc_combo)
        
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setMaximumHeight(280)
        table.setMinimumWidth(600)
        table.resizeRowsToContents()
        return table
    
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
    
    def get_table_cc_values(self, table):
        values = []
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                combo = table.cellWidget(row, col)
                values.append(self.get_cc_value(combo))
        return values
    
    def set_table_cc_values(self, table, values):
        idx = 0
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                if idx < len(values):
                    combo = table.cellWidget(row, col)
                    self.set_cc_value(combo, values[idx])
                    idx += 1
    
    def get_restart_cc_values(self):
        """Get restart CCs from the main table (last row)"""
        restart_values = []
        for col in range(4):
            combo = self.main_table.cellWidget(5, col)
            restart_values.append(self.get_cc_value(combo))
        return restart_values
    
    def set_restart_cc_values(self, values):
        """Set restart CCs in the main table (last row)"""
        for col in range(4):
            if col < len(values):
                combo = self.main_table.cellWidget(5, col)
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
            
            # 2. Send main loop CCs (excluding restart row)
            main_values = []
            for row in range(5):
                for col in range(4):
                    combo = self.main_table.cellWidget(row, col)
                    main_values.append(self.get_cc_value(combo))
            
            if not self.device.keyboard.set_thruloop_main_ccs(main_values):
                raise RuntimeError("Failed to set main CCs")
            
            # 3. Send overdub CCs (now including restart row - 24 values total)
            overdub_values = self.get_table_cc_values(self.overdub_table)  # Now returns 24 values (6 rows × 4 cols)
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
        
        # Set main table CCs (first 5 rows only)
        if 'mainCCs' in config:
            main_ccs = config.get("mainCCs", [128] * 20)
            idx = 0
            for row in range(5):
                for col in range(4):
                    if idx < len(main_ccs):
                        combo = self.main_table.cellWidget(row, col)
                        self.set_cc_value(combo, main_ccs[idx])
                        idx += 1
        
        # Set overdub table CCs (now 6 rows including restart - 24 values)
        if 'overdubCCs' in config:
            overdub_ccs = config.get("overdubCCs", [128] * 24)  # Changed from 20 to 24
            self.set_table_cc_values(self.overdub_table, overdub_ccs)
        
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
        
        # Reset all tables to None (128)
        for row in range(self.main_table.rowCount()):
            for col in range(self.main_table.columnCount()):
                combo = self.main_table.cellWidget(row, col)
                self.set_cc_value(combo, 128)
        
        for row in range(self.overdub_table.rowCount()):
            for col in range(self.overdub_table.columnCount()):
                combo = self.overdub_table.cellWidget(row, col)
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
            "mainCCs": [self.get_cc_value(self.main_table.cellWidget(row, col)) 
                       for row in range(5) for col in range(4)],
            "overdubCCs": self.get_table_cc_values(self.overdub_table),  # Now returns 24 values (6 rows × 4 cols)
            "navCCs": [self.get_cc_value(combo) for combo in self.nav_combos]
        }
        return config
    
    def valid(self):
        return isinstance(self.device, VialKeyboard)
    
    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return


class MIDIswitchSettingsConfigurator(BasicEditor):
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        self.addStretch()
        
        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        main_widget.setMinimumWidth(800)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.addWidget(main_widget)
        self.setAlignment(main_widget, QtCore.Qt.AlignHCenter)
        
        # Basic Settings Group
        basic_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "Basic Settings"))
        basic_layout = QGridLayout()
        basic_layout.setHorizontalSpacing(25)
        basic_layout.setColumnStretch(1, 0)
        basic_layout.setColumnStretch(3, 0)
        basic_layout.setColumnStretch(5, 0)
        basic_layout.setColumnStretch(6, 1)  # Push everything left
        basic_group.setLayout(basic_layout)
        main_layout.addWidget(basic_group)
        
        # Transpose
        basic_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), 0, 0)
        self.transpose_number = QComboBox()
        self.transpose_number.setMinimumWidth(120)
        for i in range(-64, 65):
            self.transpose_number.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.transpose_number.setCurrentIndex(64)
        basic_layout.addWidget(self.transpose_number, 0, 1)
        
        # Channel
        basic_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), 0, 2)
        self.channel_number = QComboBox()
        self.channel_number.setMinimumWidth(120)
        for i in range(16):
            self.channel_number.addItem(str(i + 1), i)
        basic_layout.addWidget(self.channel_number, 0, 3)
        
        # Velocity
        basic_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity:")), 0, 4)
        self.velocity_number = QComboBox()
        self.velocity_number.setMinimumWidth(120)
        for i in range(1, 128):
            self.velocity_number.addItem(str(i), i)
        self.velocity_number.setCurrentIndex(126)
        basic_layout.addWidget(self.velocity_number, 0, 5)
        
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
        
        # Unsynced Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sync Mode:")), 0, 1)
        self.unsynced_mode = QComboBox()
        self.unsynced_mode.setMinimumWidth(120)
        self.unsynced_mode.addItem("Loop", 0)
        self.unsynced_mode.addItem("BPM 1", 1)
        self.unsynced_mode.addItem("No Sync", 2)
        loop_layout.addWidget(self.unsynced_mode, 0, 2)
        
        # Sample Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sample Mode:")), 0, 3)
        self.sample_mode = QComboBox()
        self.sample_mode.setMinimumWidth(120)
        self.sample_mode.addItem("Off", False)
        self.sample_mode.addItem("On", True)
        loop_layout.addWidget(self.sample_mode, 0, 4)
        
        # Loop Messaging
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Thruloop:")), 1, 1)
        self.loop_messaging_enabled = QComboBox()
        self.loop_messaging_enabled.setMinimumWidth(120)
        self.loop_messaging_enabled.addItem("Off", False)
        self.loop_messaging_enabled.addItem("On", True)
        loop_layout.addWidget(self.loop_messaging_enabled, 1, 2)
        
        # Messaging Channel
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Thruloop Channel:")), 1, 3)
        self.loop_messaging_channel = QComboBox()
        self.loop_messaging_channel.setMinimumWidth(120)
        for i in range(1, 17):
            self.loop_messaging_channel.addItem(str(i), i)
        self.loop_messaging_channel.setCurrentIndex(15)
        loop_layout.addWidget(self.loop_messaging_channel, 1, 4)
        
        # Sync MIDI Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "ThruLoop Restart Messaging:")), 2, 1)
        self.sync_midi_mode = QComboBox()
        self.sync_midi_mode.setMinimumWidth(120)
        self.sync_midi_mode.addItem("Off", False)
        self.sync_midi_mode.addItem("On", True)
        loop_layout.addWidget(self.sync_midi_mode, 2, 2)
        
        # Restart Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Thruloop Restart Mode:")), 2, 3)
        self.alternate_restart_mode = QComboBox()
        self.alternate_restart_mode.setMinimumWidth(120)
        self.alternate_restart_mode.addItem("Restart CC", False)
        self.alternate_restart_mode.addItem("Stop+Start", True)
        loop_layout.addWidget(self.alternate_restart_mode, 2, 4)
        
        # SmartChord Lights
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Overdub Mode:")), 3, 1)
        self.smart_chord_light = QComboBox()
        self.smart_chord_light.setMinimumWidth(120)
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
        self.velocity_sensitivity = QComboBox()
        self.velocity_sensitivity.setMinimumWidth(120)
        for i in range(1, 11):
            self.velocity_sensitivity.addItem(str(i), i)
        advanced_layout.addWidget(self.velocity_sensitivity, 0, 2)
        
        # CC Interval
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "CC Interval:")), 0, 3)
        self.cc_sensitivity = QComboBox()
        self.cc_sensitivity.setMinimumWidth(120)
        for i in range(1, 17):
            self.cc_sensitivity.addItem(str(i), i)
        advanced_layout.addWidget(self.cc_sensitivity, 0, 4)
        
        # Velocity Shuffle
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Shuffle:")), 1, 1)
        self.random_velocity_modifier = QComboBox()
        self.random_velocity_modifier.setMinimumWidth(120)
        for i in range(17):
            self.random_velocity_modifier.addItem(str(i), i)
        advanced_layout.addWidget(self.random_velocity_modifier, 1, 2)
        
        # OLED Keyboard
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "OLED Keyboard:")), 1, 3)
        self.oled_keyboard = QComboBox()
        self.oled_keyboard.setMinimumWidth(120)
        self.oled_keyboard.addItem("Style 1", 0)
        self.oled_keyboard.addItem("Style 2", 12)
        advanced_layout.addWidget(self.oled_keyboard, 1, 4)

        # SC Light Mode
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Guide Lights:")), 2, 1)
        self.smart_chord_light_mode = QComboBox()
        self.smart_chord_light_mode.setMinimumWidth(120)
        self.smart_chord_light_mode.addItem("All Off", 1)
        self.smart_chord_light_mode.addItem("SmartChord Off", 2)
        self.smart_chord_light_mode.addItem("All On: Dynamic", 0)
        self.smart_chord_light_mode.addItem("All on: Guitar EADGB", 3)
        self.smart_chord_light_mode.addItem("All on: Guitar ADGBE", 4)
        advanced_layout.addWidget(self.smart_chord_light_mode, 2, 2)
        
        # Colorblind Mode
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Colorblind Mode:")), 2, 3)
        self.colorblind_mode = QComboBox()
        self.colorblind_mode.setMinimumWidth(120)
        self.colorblind_mode.addItem("Off", 0)
        self.colorblind_mode.addItem("On", 1)
        advanced_layout.addWidget(self.colorblind_mode, 2, 4)
        
        # RGB Layer Mode
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "RGB Layer Mode:")), 3, 1)
        self.custom_layer_animations = QComboBox()
        self.custom_layer_animations.setMinimumWidth(120)
        self.custom_layer_animations.addItem("Off", False)
        self.custom_layer_animations.addItem("On", True)
        advanced_layout.addWidget(self.custom_layer_animations, 3, 2)
        
        # CC Loop Recording
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "CC Loop Recording:")), 3, 3)
        self.cc_loop_recording = QComboBox()
        self.cc_loop_recording.setMinimumWidth(120)
        self.cc_loop_recording.addItem("Off", False)
        self.cc_loop_recording.addItem("On", True)
        advanced_layout.addWidget(self.cc_loop_recording, 3, 4)
        
        # True Sustain
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "True Sustain:")), 4, 1)
        self.true_sustain = QComboBox()
        self.true_sustain.setMinimumWidth(120)
        self.true_sustain.addItem("Off", False)
        self.true_sustain.addItem("On", True)
        advanced_layout.addWidget(self.true_sustain, 4, 2)
        
        # KeySplit Modes Group
        keysplit_modes_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "KeySplit Modes"))
        keysplit_modes_layout = QGridLayout()
        keysplit_modes_layout.setHorizontalSpacing(25)
        keysplit_modes_layout.setColumnStretch(1, 0)
        keysplit_modes_layout.setColumnStretch(3, 0)
        keysplit_modes_layout.setColumnStretch(5, 0)
        keysplit_modes_layout.setColumnStretch(6, 1)  # Push everything left
        keysplit_modes_group.setLayout(keysplit_modes_layout)
        main_layout.addWidget(keysplit_modes_group)
        
        # Channel Mode
        keysplit_modes_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), 0, 0)
        self.key_split_status = QComboBox()
        self.key_split_status.setMinimumWidth(120)
        self.key_split_status.addItem("Disable Keysplit", 0)
        self.key_split_status.addItem("KeySplit On", 1)
        self.key_split_status.addItem("TripleSplit On", 2)
        keysplit_modes_layout.addWidget(self.key_split_status, 0, 1)
        
        # Transpose Mode
        keysplit_modes_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), 0, 2)
        self.key_split_transpose_status = QComboBox()
        self.key_split_transpose_status.setMinimumWidth(120)
        self.key_split_transpose_status.addItem("Disable Keysplit", 0)
        self.key_split_transpose_status.addItem("KeySplit On", 1)
        self.key_split_transpose_status.addItem("TripleSplit On", 2)
        keysplit_modes_layout.addWidget(self.key_split_transpose_status, 0, 3)
        
        # Velocity Mode
        keysplit_modes_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity:")), 0, 4)
        self.key_split_velocity_status = QComboBox()
        self.key_split_velocity_status.setMinimumWidth(120)
        self.key_split_velocity_status.addItem("Disable Keysplit", 0)
        self.key_split_velocity_status.addItem("KeySplit On", 1)
        self.key_split_velocity_status.addItem("TripleSplit On", 2)
        keysplit_modes_layout.addWidget(self.key_split_velocity_status, 0, 5)
        
        # KeySplit Settings Group
        keysplit_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "KeySplit & TripleSplit Settings"))
        keysplit_layout = QGridLayout()
        keysplit_layout.setHorizontalSpacing(25)
        keysplit_layout.setColumnStretch(0, 1)    # Left spacer
        keysplit_layout.setColumnStretch(2, 0)
        keysplit_layout.setColumnStretch(4, 0)
        keysplit_layout.setColumnStretch(5, 1)    # Right spacer - pushes everything toward center
        keysplit_group.setLayout(keysplit_layout)
        main_layout.addWidget(keysplit_group)
        
        # KeySplit settings (left column)
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "KeySplit Settings")), 0, 1, 1, 2)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), 1, 1)
        self.key_split_channel = QComboBox()
        self.key_split_channel.setMinimumWidth(120)
        for i in range(16):
            self.key_split_channel.addItem(str(i + 1), i)
        keysplit_layout.addWidget(self.key_split_channel, 1, 2)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), 2, 1)
        self.transpose_number2 = QComboBox()
        self.transpose_number2.setMinimumWidth(120)
        for i in range(-64, 65):
            self.transpose_number2.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.transpose_number2.setCurrentIndex(64)
        keysplit_layout.addWidget(self.transpose_number2, 2, 2)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity:")), 3, 1)
        self.velocity_number2 = QComboBox()
        self.velocity_number2.setMinimumWidth(120)
        for i in range(1, 128):
            self.velocity_number2.addItem(str(i), i)
        self.velocity_number2.setCurrentIndex(126)
        keysplit_layout.addWidget(self.velocity_number2, 3, 2)
        
        # TripleSplit settings (right column)
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "TripleSplit Settings")), 0, 3, 1, 2)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), 1, 3)
        self.key_split2_channel = QComboBox()
        self.key_split2_channel.setMinimumWidth(120)
        for i in range(16):
            self.key_split2_channel.addItem(str(i + 1), i)
        keysplit_layout.addWidget(self.key_split2_channel, 1, 4)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), 2, 3)
        self.transpose_number3 = QComboBox()
        self.transpose_number3.setMinimumWidth(120)
        for i in range(-64, 65):
            self.transpose_number3.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.transpose_number3.setCurrentIndex(64)
        keysplit_layout.addWidget(self.transpose_number3, 2, 4)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity:")), 3, 3)
        self.velocity_number3 = QComboBox()
        self.velocity_number3.setMinimumWidth(120)
        for i in range(1, 128):
            self.velocity_number3.addItem(str(i), i)
        self.velocity_number3.setCurrentIndex(126)
        keysplit_layout.addWidget(self.velocity_number3, 3, 4)
        
        # Buttons
        self.addStretch()
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        # Default buttons
        save_default_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Save as Default"))
        save_default_btn.clicked.connect(lambda: self.on_save_slot(0))
        buttons_layout.addWidget(save_default_btn)
        
        load_default_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Load Default"))
        load_default_btn.clicked.connect(lambda: self.on_load_slot(0))
        buttons_layout.addWidget(load_default_btn)
        
        load_current_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Load Current Settings"))
        load_current_btn.clicked.connect(self.on_load_current_settings)
        buttons_layout.addWidget(load_current_btn)
        
        reset_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Reset to Defaults"))
        reset_btn.clicked.connect(self.on_reset)
        buttons_layout.addWidget(reset_btn)
        
        self.addLayout(buttons_layout)
        
        # Save slot buttons
        save_slots_layout = QHBoxLayout()
        save_slots_layout.addStretch()
        for i in range(1, 5):
            btn = QPushButton(tr("MIDIswitchSettingsConfigurator", f"Save to Slot {i}"))
            btn.clicked.connect(lambda checked, slot=i: self.on_save_slot(slot))
            save_slots_layout.addWidget(btn)
        self.addLayout(save_slots_layout)
        
        # Load slot buttons
        load_slots_layout = QHBoxLayout()
        load_slots_layout.addStretch()
        for i in range(1, 5):
            btn = QPushButton(tr("MIDIswitchSettingsConfigurator", f"Load Slot {i}"))
            btn.clicked.connect(lambda checked, slot=i: self.on_load_slot(slot))
            load_slots_layout.addWidget(btn)
        self.addLayout(load_slots_layout)
    
    def get_current_settings(self):
        """Get current UI settings as dictionary"""
        return {
            "velocity_sensitivity": self.velocity_sensitivity.currentData(),
            "cc_sensitivity": self.cc_sensitivity.currentData(),
            "channel_number": self.channel_number.currentData(),
            "transpose_number": self.transpose_number.currentData(),
            "transpose_number2": self.transpose_number2.currentData(),
            "transpose_number3": self.transpose_number3.currentData(),
            "velocity_number": self.velocity_number.currentData(),
            "velocity_number2": self.velocity_number2.currentData(),
            "velocity_number3": self.velocity_number3.currentData(),
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
            "truesustain": self.true_sustain.currentData()
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
        set_combo_by_data(self.channel_number, config.get("channel_number"), 0)
        set_combo_by_data(self.transpose_number, config.get("transpose_number"), 0)
        set_combo_by_data(self.transpose_number2, config.get("transpose_number2"), 0)
        set_combo_by_data(self.transpose_number3, config.get("transpose_number3"), 0)
        set_combo_by_data(self.velocity_number, config.get("velocity_number"), 127)
        set_combo_by_data(self.velocity_number2, config.get("velocity_number2"), 127)
        set_combo_by_data(self.velocity_number3, config.get("velocity_number3"), 127)
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
    
    def pack_basic_data(self, settings):
        """Pack basic settings into 26-byte structure"""
        data = bytearray(26)
        
        struct.pack_into('<I', data, 0, settings["velocity_sensitivity"])
        struct.pack_into('<I', data, 4, settings["cc_sensitivity"])
        
        offset = 8
        data[offset] = settings["channel_number"]; offset += 1
        data[offset] = settings["transpose_number"] & 0xFF; offset += 1
        data[offset] = 0; offset += 1  # octave_number
        data[offset] = settings["transpose_number2"] & 0xFF; offset += 1
        data[offset] = 0; offset += 1  # octave_number2
        data[offset] = settings["transpose_number3"] & 0xFF; offset += 1
        data[offset] = 0; offset += 1  # octave_number3
        data[offset] = settings["velocity_number"]; offset += 1
        data[offset] = settings["velocity_number2"]; offset += 1
        data[offset] = settings["velocity_number3"]; offset += 1
        data[offset] = settings["random_velocity_modifier"]; offset += 1
        
        struct.pack_into('<I', data, offset, settings["oled_keyboard"]); offset += 4
        
        data[offset] = settings["smart_chord_light"]; offset += 1
        data[offset] = settings["smart_chord_light_mode"]; offset += 1
        
        return data
    
    def pack_advanced_data(self, settings):
        """Pack advanced settings into 15-byte structure"""
        data = bytearray(15)
        
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
            "channel_number": 0,
            "transpose_number": 0,
            "transpose_number2": 0,
            "transpose_number3": 0,
            "velocity_number": 127,
            "velocity_number2": 127,
            "velocity_number3": 127,
            "random_velocity_modifier": 0,
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
            "truesustain": False
        }
        self.apply_settings(defaults)
    
    def valid(self):
        return isinstance(self.device, VialKeyboard)
    
    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return
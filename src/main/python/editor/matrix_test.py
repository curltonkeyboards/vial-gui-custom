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
        
        # HID Command constants (0xB0-0xB5 range)
        self.HID_CMD_SET_LOOP_CONFIG = 0xB0
        self.HID_CMD_SET_MAIN_LOOP_CCS = 0xB1
        self.HID_CMD_SET_OVERDUB_CCS = 0xB2
        self.HID_CMD_SET_NAVIGATION_CONFIG = 0xB3
        self.HID_CMD_GET_ALL_CONFIG = 0xB4
        self.HID_CMD_RESET_LOOP_CONFIG = 0xB5
        
        self.MANUFACTURER_ID = 0x7D
        self.SUB_ID = 0x00
        self.DEVICE_ID = 0x4D
        
        # Initialize references to None - will be set in setup_ui
        self.single_loopchop_label = None
        self.master_cc = None
        self.single_loopchop_widgets = []
        self.nav_widget = None
        
        self.setup_ui()
        
    def setup_ui(self):
        self.addStretch()
        
        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        main_widget.setMinimumWidth(1000)  # Make it wider
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.addWidget(main_widget)
        self.setAlignment(main_widget, QtCore.Qt.AlignHCenter)
        
        # Top row: Basic Settings and LoopChop side by side
        top_row_layout = QHBoxLayout()
        main_layout.addLayout(top_row_layout)
        
        # Basic Settings Group
        basic_group = QGroupBox(tr("ThruLoopConfigurator", "Basic Settings"))
        basic_layout = QGridLayout()
        basic_group.setLayout(basic_layout)
        top_row_layout.addWidget(basic_group)
        
        # ThruLoop Channel
        basic_layout.addWidget(QLabel(tr("ThruLoopConfigurator", "ThruLoop Channel")), 0, 0)
        self.loop_channel = QComboBox()
        self.loop_channel.setMinimumWidth(150)
        self.loop_channel.setMaximumHeight(25)
        self.loop_channel.view().setMaximumHeight(200)  # Add scroll for dropdown
        for i in range(1, 17):
            self.loop_channel.addItem(f"Channel {i}", i)
        self.loop_channel.setCurrentIndex(15)  # Default to channel 16
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
        loopchop_group = QGroupBox(tr("ThruLoopConfigurator", "LoopChop"))
        loopchop_layout = QGridLayout()
        loopchop_layout.setSpacing(5)  # Reduce spacing
        loopchop_layout.setContentsMargins(10, 10, 10, 10)  # Smaller margins
        loopchop_group.setLayout(loopchop_layout)
        top_row_layout.addWidget(loopchop_group)
        
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
        nav_layout.setSpacing(3)  # Minimal spacing
        self.nav_combos = []
        for i in range(8):
            row = i // 4
            col = i % 4
            label = QLabel(f"{i}/8")
            label.setMaximumWidth(30)  # Smaller labels
            nav_layout.addWidget(label, row * 2, col)
            combo = self.create_cc_combo()
            nav_layout.addWidget(combo, row * 2 + 1, col)
            self.nav_combos.append(combo)
        
        self.nav_widget = QWidget()
        self.nav_widget.setLayout(nav_layout)
        loopchop_layout.addWidget(self.nav_widget, 2, 0, 1, 4)
        
        # Main Functions Table (bigger to prevent cutoff)
        main_group = QGroupBox(tr("ThruLoopConfigurator", "Main Functions"))
        main_layout.addWidget(main_group)
        self.main_table = self.create_main_function_table()
        main_group_layout = QVBoxLayout()
        main_group_layout.addWidget(self.main_table)
        main_group.setLayout(main_group_layout)
        self.main_group = main_group
        
        # Overdub Functions Table  
        overdub_group = QGroupBox(tr("ThruLoopConfigurator", "Overdub Functions"))
        main_layout.addWidget(overdub_group)
        self.overdub_table = self.create_function_table()
        overdub_group_layout = QVBoxLayout()
        overdub_group_layout.addWidget(self.overdub_table)
        overdub_group.setLayout(overdub_group_layout)
        self.overdub_group = overdub_group
        
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
        
        self.addLayout(buttons_layout)
        
        # Apply stylesheet to prevent bold focus styling
        self.setStyleSheet("""
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
        combo = QComboBox()
        combo.setMinimumWidth(120)  # Make combo boxes wider
        combo.setMaximumHeight(25)  # Limit height
        combo.view().setMaximumHeight(200)  # Add scroll bar for dropdown
        combo.addItem("None", 128)
        for i in range(128):
            combo.addItem(f"CC# {i}", i)
        combo.setCurrentIndex(0)  # Default to "None"
        return combo
    
    def create_function_table(self):
        table = QTableWidget(5, 4)  # 5 functions x 4 loops
        table.setHorizontalHeaderLabels([f"Loop {i+1}" for i in range(4)])
        table.setVerticalHeaderLabels([
            "Start Recording", "Stop Recording", "Start Playing", "Stop Playing", "Clear"
        ])
        
        # Fill table with CC combo boxes
        for row in range(5):
            for col in range(4):
                combo = self.create_cc_combo()
                table.setCellWidget(row, col, combo)
        
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setMaximumHeight(200)
        table.setMinimumWidth(600)  # Make table wider
        return table
    
    def create_main_function_table(self):
        table = QTableWidget(6, 4)  # 6 functions x 4 loops (added Restart row)
        table.setHorizontalHeaderLabels([f"Loop {i+1}" for i in range(4)])
        table.setVerticalHeaderLabels([
            "Start Recording", "Stop Recording", "Start Playing", "Stop Playing", "Clear", "Restart"
        ])
        
        # Fill table with CC combo boxes
        for row in range(6):
            for col in range(4):
                combo = self.create_cc_combo()
                table.setCellWidget(row, col, combo)
        
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setMaximumHeight(280)  # Increased height to prevent cutoff
        table.setMinimumWidth(600)  # Make table wider
        table.resizeRowsToContents()  # Auto-resize rows
        return table
    
    def on_loop_enabled_changed(self):
        # When checked, ThruLoop is disabled (reversed logic from webapp)
        enabled = not self.loop_enabled.isChecked()
        self.main_group.setEnabled(enabled)
        self.overdub_group.setEnabled(enabled) 
        self.loopchop_group.setEnabled(enabled)
    
    def on_separate_loopchop_changed(self):
        # Show/hide based on checkbox state but don't completely hide widgets
        separate = self.separate_loopchop.isChecked()
        # Enable/disable instead of hide/show
        if self.single_loopchop_label:
            self.single_loopchop_label.setEnabled(not separate)
        if self.master_cc:
            self.master_cc.setEnabled(not separate)
        if self.nav_widget:
            self.nav_widget.setEnabled(separate)
    
    def send_hid_packet(self, command, macro_num, data):
        """Send HID packet to device"""
        if not self.device or not isinstance(self.device, VialKeyboard):
            return
        
        packet = bytearray(32)
        packet[0] = self.MANUFACTURER_ID
        packet[1] = self.SUB_ID  
        packet[2] = self.DEVICE_ID
        packet[3] = command
        packet[4] = macro_num
        packet[5] = 0  # Status
        
        # Copy data payload (max 26 bytes)
        data_len = min(len(data), 26)
        packet[6:6+data_len] = data[:data_len]
        
        try:
            self.device.keyboard.via_command(packet)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send command: {str(e)}")
    
    def get_cc_value(self, combo):
        return combo.currentData()
    
    def set_cc_value(self, combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                break
    
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
            combo = self.main_table.cellWidget(5, col)  # Row 5 is the Restart row
            restart_values.append(self.get_cc_value(combo))
        return restart_values
    
    def set_restart_cc_values(self, values):
        """Set restart CCs in the main table (last row)"""
        for col in range(4):
            if col < len(values):
                combo = self.main_table.cellWidget(5, col)  # Row 5 is the Restart row
                self.set_cc_value(combo, values[col])
    
    def on_save(self):
        """Save all configuration to keyboard"""
        try:
            # 1. Send basic loop configuration
            loop_config_data = [
                0 if self.loop_enabled.isChecked() else 1,  # Reversed logic
                self.loop_channel.currentData(),
                1 if self.sync_midi.isChecked() else 0,
                1 if self.alternate_restart.isChecked() else 0,
            ]
            # Add restart CCs from main table instead
            restart_values = self.get_restart_cc_values()
            loop_config_data.extend(restart_values)
            # Add CC loop recording
            loop_config_data.append(1 if self.cc_loop_recording.isChecked() else 0)
            
            self.send_hid_packet(self.HID_CMD_SET_LOOP_CONFIG, 0, loop_config_data)
            
            # 2. Send main loop CCs (excluding restart row)
            main_values = []
            for row in range(5):  # Only first 5 rows (excluding restart)
                for col in range(4):
                    combo = self.main_table.cellWidget(row, col)
                    main_values.append(self.get_cc_value(combo))
            self.send_hid_packet(self.HID_CMD_SET_MAIN_LOOP_CCS, 0, main_values)
            
            # 3. Send overdub CCs  
            overdub_values = self.get_table_cc_values(self.overdub_table)
            self.send_hid_packet(self.HID_CMD_SET_OVERDUB_CCS, 0, overdub_values)
            
            # 4. Send navigation configuration
            nav_config_data = [
                1 if self.separate_loopchop.isChecked() else 0,
                self.get_cc_value(self.master_cc),
            ]
            for combo in self.nav_combos:
                nav_config_data.append(self.get_cc_value(combo))
            
            self.send_hid_packet(self.HID_CMD_SET_NAVIGATION_CONFIG, 0, nav_config_data)
            
            QMessageBox.information(self, "Success", "ThruLoop configuration saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
    
    def on_load_from_keyboard(self):
        """Load configuration from keyboard"""
        try:
            self.send_hid_packet(self.HID_CMD_GET_ALL_CONFIG, 0, [])
            QMessageBox.information(self, "Info", "Load request sent to keyboard")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load from keyboard: {str(e)}")
    
    def get_current_config(self):
        """Get current UI configuration as dictionary"""
        config = {
            "version": "1.0",
            "loopEnabled": not self.loop_enabled.isChecked(),  # Reversed for file storage
            "loopChannel": self.loop_channel.currentData(), 
            "syncMidi": self.sync_midi.isChecked(),
            "alternateRestart": self.alternate_restart.isChecked(),
            "ccLoopRecording": self.cc_loop_recording.isChecked(),
            "separateLoopChopCC": self.separate_loopchop.isChecked(),
            "masterCC": self.get_cc_value(self.master_cc),
            "restartCCs": self.get_restart_cc_values(),
            "mainCCs": [self.get_cc_value(self.main_table.cellWidget(row, col)) 
                       for row in range(5) for col in range(4)],  # First 5 rows only
            "overdubCCs": self.get_table_cc_values(self.overdub_table),
            "navCCs": [self.get_cc_value(combo) for combo in self.nav_combos]
        }
        return config
    
    def apply_config(self, config):
        """Apply configuration dictionary to UI"""
        self.loop_enabled.setChecked(not config.get("loopEnabled", True))  # Reversed
        
        # Set channel
        for i in range(self.loop_channel.count()):
            if self.loop_channel.itemData(i) == config.get("loopChannel", 16):
                self.loop_channel.setCurrentIndex(i)
                break
        
        self.sync_midi.setChecked(config.get("syncMidi", False))
        self.alternate_restart.setChecked(config.get("alternateRestart", False))
        self.cc_loop_recording.setChecked(config.get("ccLoopRecording", False))
        self.separate_loopchop.setChecked(config.get("separateLoopChopCC", False))
        self.set_cc_value(self.master_cc, config.get("masterCC", 128))
        
        # Set restart CCs
        restart_ccs = config.get("restartCCs", [128] * 4)
        self.set_restart_cc_values(restart_ccs)
        
        # Set main table CCs (first 5 rows only)
        main_ccs = config.get("mainCCs", [128] * 20)
        idx = 0
        for row in range(5):
            for col in range(4):
                if idx < len(main_ccs):
                    combo = self.main_table.cellWidget(row, col)
                    self.set_cc_value(combo, main_ccs[idx])
                    idx += 1
        
        # Set overdub table CCs
        overdub_ccs = config.get("overdubCCs", [128] * 20)  
        self.set_table_cc_values(self.overdub_table, overdub_ccs)
        
        # Set navigation CCs
        nav_ccs = config.get("navCCs", [128] * 8)
        for i, combo in enumerate(self.nav_combos):
            if i < len(nav_ccs):
                self.set_cc_value(combo, nav_ccs[i])
        
        # Update UI state
        self.on_loop_enabled_changed()
        self.on_separate_loopchop_changed()
    
    def valid(self):
        return isinstance(self.device, VialKeyboard)
    
    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return
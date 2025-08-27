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
        
        # HID Command constants (0xB0-0xB5 range) - SAME AS WEBAPP
        self.HID_CMD_SET_LOOP_CONFIG = 0xB0
        self.HID_CMD_SET_MAIN_LOOP_CCS = 0xB1
        self.HID_CMD_SET_OVERDUB_CCS = 0xB2
        self.HID_CMD_SET_NAVIGATION_CONFIG = 0xB3
        self.HID_CMD_GET_ALL_CONFIG = 0xB4
        self.HID_CMD_RESET_LOOP_CONFIG = 0xB5
        
        # SAME AS WEBAPP
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
        
        # Basic Settings Group - ASSIGN TO SELF
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
        
        # LoopChop Settings (more compact) - ASSIGN TO SELF
        self.loopchop_group = QGroupBox(tr("ThruLoopConfigurator", "LoopChop"))
        loopchop_layout = QGridLayout()
        loopchop_layout.setSpacing(5)  # Reduce spacing
        loopchop_layout.setContentsMargins(10, 10, 10, 10)  # Smaller margins
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
            
        combo.setCurrentIndex(0)  # Default to "None"
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
        # If not found, set to None
        combo.setCurrentIndex(0)
    
    def create_function_table(self):
        table = QTableWidget(5, 4)  # 5 functions x 4 loops
        table.setHorizontalHeaderLabels([f"Loop {i+1}" for i in range(4)])
        table.setVerticalHeaderLabels([
            "Start Recording", "Stop Recording", "Start Playing", "Stop Playing", "Clear"
        ])
        
        # Fill table with CC combos
        for row in range(5):
            for col in range(4):
                cc_combo = self.create_cc_combo()
                table.setCellWidget(row, col, cc_combo)
        
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setMaximumHeight(200)
        table.setMinimumWidth(600)
        return table
    
    def create_main_function_table(self):
        table = QTableWidget(6, 4)  # 6 functions x 4 loops (added Restart row)
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
        """Send HID packet to device - EXACTLY LIKE WEBAPP"""
        if not self.device or not isinstance(self.device, VialKeyboard):
            raise RuntimeError("Device not connected")
        
        # Create 32-byte packet EXACTLY like webapp
        packet = bytearray(32)
        packet[0] = self.MANUFACTURER_ID  # 0x7D
        packet[1] = self.SUB_ID           # 0x00
        packet[2] = self.DEVICE_ID        # 0x4D
        packet[3] = command
        packet[4] = macro_num
        packet[5] = 0  # Status
        
        # Copy data payload (max 26 bytes)
        data_len = min(len(data), 26)
        packet[6:6+data_len] = data[:data_len]
        
        try:
            # Send via Vial's via_command method
            self.device.keyboard.via_command(bytes(packet))
        except Exception as e:
            raise RuntimeError(f"Failed to send command: {str(e)}")
    
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
            
            QMessageBox.information(None, "Success", "ThruLoop configuration saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save configuration: {str(e)}")
    
    def on_load_from_keyboard(self):
        """Load configuration from keyboard"""
        try:
            self.send_hid_packet(self.HID_CMD_GET_ALL_CONFIG, 0, [])
            QMessageBox.information(None, "Info", "Load request sent to keyboard")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to load from keyboard: {str(e)}")
    
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


class MIDIswitchSettingsConfigurator(BasicEditor):
    
    def __init__(self):
        super().__init__()
        
        # HID Command constants (0xB6-0xBB range) - SAME AS WEBAPP
        self.HID_CMD_SET_KEYBOARD_CONFIG = 0xB6
        self.HID_CMD_GET_KEYBOARD_CONFIG = 0xB7
        self.HID_CMD_RESET_KEYBOARD_CONFIG = 0xB8
        self.HID_CMD_SAVE_KEYBOARD_SLOT = 0xB9
        self.HID_CMD_LOAD_KEYBOARD_SLOT = 0xBA
        self.HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED = 0xBB
        
        # SAME AS WEBAPP
        self.MANUFACTURER_ID = 0x7D
        self.SUB_ID = 0x00
        self.DEVICE_ID = 0x4D
        
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
        
        # Basic Settings Group
        basic_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "Basic Settings"))
        basic_layout = QGridLayout()
        basic_group.setLayout(basic_layout)
        main_layout.addWidget(basic_group)
        
        # Transpose
        basic_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), 0, 0)
        self.transpose_number = QComboBox()
        self.transpose_number.setMinimumWidth(120)  # Make wider
        for i in range(-64, 65):
            self.transpose_number.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.transpose_number.setCurrentIndex(64)  # Default to 0
        basic_layout.addWidget(self.transpose_number, 0, 1)
        
        # Channel
        basic_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), 0, 2)
        self.channel_number = QComboBox()
        self.channel_number.setMinimumWidth(120)  # Make wider
        for i in range(16):
            self.channel_number.addItem(str(i + 1), i)
        basic_layout.addWidget(self.channel_number, 0, 3)
        
        # Velocity
        basic_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity:")), 0, 4)
        self.velocity_number = QComboBox()
        self.velocity_number.setMinimumWidth(120)  # Make wider
        for i in range(1, 128):
            self.velocity_number.addItem(str(i), i)
        self.velocity_number.setCurrentIndex(126)  # Default to 127
        basic_layout.addWidget(self.velocity_number, 0, 5)
        
        # Loop Settings Group
        loop_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "Loop Settings"))
        loop_layout = QGridLayout()
        loop_group.setLayout(loop_layout)
        main_layout.addWidget(loop_group)
        
        # Unsynced Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Unsynced Mode:")), 0, 0)
        self.unsynced_mode = QComboBox()
        self.unsynced_mode.setMinimumWidth(120)  # Make wider
        self.unsynced_mode.addItem("Off", False)
        self.unsynced_mode.addItem("On", True)
        loop_layout.addWidget(self.unsynced_mode, 0, 1)
        
        # Sample Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sample Mode:")), 0, 2)
        self.sample_mode = QComboBox()
        self.sample_mode.setMinimumWidth(120)  # Make wider
        self.sample_mode.addItem("Off", False)
        self.sample_mode.addItem("On", True)
        loop_layout.addWidget(self.sample_mode, 0, 3)
        
        # Loop Messaging
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Loop Messaging:")), 1, 0)
        self.loop_messaging_enabled = QComboBox()
        self.loop_messaging_enabled.setMinimumWidth(120)  # Make wider
        self.loop_messaging_enabled.addItem("Off", False)
        self.loop_messaging_enabled.addItem("On", True)
        loop_layout.addWidget(self.loop_messaging_enabled, 1, 1)
        
        # Messaging Channel
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Messaging Channel:")), 1, 2)
        self.loop_messaging_channel = QComboBox()
        self.loop_messaging_channel.setMinimumWidth(120)  # Make wider
        for i in range(1, 17):
            self.loop_messaging_channel.addItem(str(i), i)
        self.loop_messaging_channel.setCurrentIndex(15)  # Default to 16
        loop_layout.addWidget(self.loop_messaging_channel, 1, 3)
        
        # Sync MIDI Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sync MIDI Mode:")), 2, 0)
        self.sync_midi_mode = QComboBox()
        self.sync_midi_mode.setMinimumWidth(120)  # Make wider
        self.sync_midi_mode.addItem("Off", False)
        self.sync_midi_mode.addItem("On", True)
        loop_layout.addWidget(self.sync_midi_mode, 2, 1)
        
        # Restart Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Restart Mode:")), 2, 2)
        self.alternate_restart_mode = QComboBox()
        self.alternate_restart_mode.setMinimumWidth(120)  # Make wider
        self.alternate_restart_mode.addItem("Restart CC", False)
        self.alternate_restart_mode.addItem("Stop+Start", True)
        loop_layout.addWidget(self.alternate_restart_mode, 2, 3)
        
        # Advanced Settings Group
        advanced_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "Advanced Settings"))
        advanced_layout = QGridLayout()
        advanced_group.setLayout(advanced_layout)
        main_layout.addWidget(advanced_group)
        
        # Velocity Interval
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Interval:")), 0, 0)
        self.velocity_sensitivity = QComboBox()
        self.velocity_sensitivity.setMinimumWidth(120)  # Make wider
        for i in range(1, 11):
            self.velocity_sensitivity.addItem(str(i), i)
        advanced_layout.addWidget(self.velocity_sensitivity, 0, 1)
        
        # CC Interval
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "CC Interval:")), 0, 2)
        self.cc_sensitivity = QComboBox()
        self.cc_sensitivity.setMinimumWidth(120)  # Make wider
        for i in range(1, 17):
            self.cc_sensitivity.addItem(str(i), i)
        advanced_layout.addWidget(self.cc_sensitivity, 0, 3)
        
        # Velocity Shuffle
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Shuffle:")), 1, 0)
        self.random_velocity_modifier = QComboBox()
        self.random_velocity_modifier.setMinimumWidth(120)  # Make wider
        for i in range(17):
            self.random_velocity_modifier.addItem(str(i), i)
        advanced_layout.addWidget(self.random_velocity_modifier, 1, 1)
        
        # OLED Keyboard
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "OLED Keyboard:")), 1, 2)
        self.oled_keyboard = QComboBox()
        self.oled_keyboard.setMinimumWidth(120)  # Make wider
        self.oled_keyboard.addItem("Style 1", 0)
        self.oled_keyboard.addItem("Style 2", 12)
        advanced_layout.addWidget(self.oled_keyboard, 1, 3)
        
        # SmartChord Lights
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "SmartChord Lights:")), 2, 0)
        self.smart_chord_light = QComboBox()
        self.smart_chord_light.setMinimumWidth(120)  # Make wider
        self.smart_chord_light.addItem("On", 0)
        self.smart_chord_light.addItem("Off", 3)
        advanced_layout.addWidget(self.smart_chord_light, 2, 1)
        
        # SC Light Mode
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "SC Light Mode:")), 2, 2)
        self.smart_chord_light_mode = QComboBox()
        self.smart_chord_light_mode.setMinimumWidth(120)  # Make wider
        self.smart_chord_light_mode.addItem("Custom", 0)
        self.smart_chord_light_mode.addItem("Off", 2)
        self.smart_chord_light_mode.addItem("Guitar Low E", 3)
        self.smart_chord_light_mode.addItem("Guitar High E", 4)
        advanced_layout.addWidget(self.smart_chord_light_mode, 2, 3)
        
        # RGB Layer Mode
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "RGB Layer Mode:")), 3, 0)
        self.custom_layer_animations = QComboBox()
        self.custom_layer_animations.setMinimumWidth(120)  # Make wider
        self.custom_layer_animations.addItem("Off", False)
        self.custom_layer_animations.addItem("On", True)
        advanced_layout.addWidget(self.custom_layer_animations, 3, 1)
        
        # Colorblind Mode
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Colorblind Mode:")), 3, 2)
        self.colorblind_mode = QComboBox()
        self.colorblind_mode.setMinimumWidth(120)  # Make wider
        self.colorblind_mode.addItem("Off", 0)
        self.colorblind_mode.addItem("On", 1)
        advanced_layout.addWidget(self.colorblind_mode, 3, 3)
        
        # CC Loop Recording
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "CC Loop Recording:")), 4, 0)
        self.cc_loop_recording = QComboBox()
        self.cc_loop_recording.setMinimumWidth(120)  # Make wider
        self.cc_loop_recording.addItem("Off", False)
        self.cc_loop_recording.addItem("On", True)
        advanced_layout.addWidget(self.cc_loop_recording, 4, 1)
        
        # True Sustain
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "True Sustain:")), 4, 2)
        self.true_sustain = QComboBox()
        self.true_sustain.setMinimumWidth(120)  # Make wider
        self.true_sustain.addItem("Off", False)
        self.true_sustain.addItem("On", True)
        advanced_layout.addWidget(self.true_sustain, 4, 3)
        
        # KeySplit Modes Group
        keysplit_modes_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "KeySplit Modes"))
        keysplit_modes_layout = QGridLayout()
        keysplit_modes_group.setLayout(keysplit_modes_layout)
        main_layout.addWidget(keysplit_modes_group)
        
        # Channel Mode
        keysplit_modes_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), 0, 0)
        self.key_split_status = QComboBox()
        self.key_split_status.setMinimumWidth(120)  # Make wider
        self.key_split_status.addItem("Disable Keysplit", 0)
        self.key_split_status.addItem("KeySplit On", 1)
        self.key_split_status.addItem("TripleSplit On", 2)
        keysplit_modes_layout.addWidget(self.key_split_status, 0, 1)
        
        # Transpose Mode
        keysplit_modes_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), 0, 2)
        self.key_split_transpose_status = QComboBox()
        self.key_split_transpose_status.setMinimumWidth(120)  # Make wider
        self.key_split_transpose_status.addItem("Disable Keysplit", 0)
        self.key_split_transpose_status.addItem("KeySplit On", 1)
        self.key_split_transpose_status.addItem("TripleSplit On", 2)
        keysplit_modes_layout.addWidget(self.key_split_transpose_status, 0, 3)
        
        # Velocity Mode
        keysplit_modes_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity:")), 0, 4)
        self.key_split_velocity_status = QComboBox()
        self.key_split_velocity_status.setMinimumWidth(120)  # Make wider
        self.key_split_velocity_status.addItem("Disable Keysplit", 0)
        self.key_split_velocity_status.addItem("KeySplit On", 1)
        self.key_split_velocity_status.addItem("TripleSplit On", 2)
        keysplit_modes_layout.addWidget(self.key_split_velocity_status, 0, 5)
        
        # KeySplit Settings Group
        keysplit_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "KeySplit & TripleSplit Settings"))
        keysplit_layout = QGridLayout()
        keysplit_group.setLayout(keysplit_layout)
        main_layout.addWidget(keysplit_group)
        
        # KeySplit settings (left column)
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "KeySplit Settings")), 0, 0, 1, 2)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), 1, 0)
        self.key_split_channel = QComboBox()
        self.key_split_channel.setMinimumWidth(120)  # Make wider
        for i in range(16):
            self.key_split_channel.addItem(str(i + 1), i)
        keysplit_layout.addWidget(self.key_split_channel, 1, 1)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), 2, 0)
        self.transpose_number2 = QComboBox()
        self.transpose_number2.setMinimumWidth(120)  # Make wider
        for i in range(-64, 65):
            self.transpose_number2.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.transpose_number2.setCurrentIndex(64)  # Default to 0
        keysplit_layout.addWidget(self.transpose_number2, 2, 1)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity:")), 3, 0)
        self.velocity_number2 = QComboBox()
        self.velocity_number2.setMinimumWidth(120)  # Make wider
        for i in range(1, 128):
            self.velocity_number2.addItem(str(i), i)
        self.velocity_number2.setCurrentIndex(126)  # Default to 127
        keysplit_layout.addWidget(self.velocity_number2, 3, 1)
        
        # TripleSplit settings (right column)
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "TripleSplit Settings")), 0, 2, 1, 2)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), 1, 2)
        self.key_split2_channel = QComboBox()
        self.key_split2_channel.setMinimumWidth(120)  # Make wider
        for i in range(16):
            self.key_split2_channel.addItem(str(i + 1), i)
        keysplit_layout.addWidget(self.key_split2_channel, 1, 3)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), 2, 2)
        self.transpose_number3 = QComboBox()
        self.transpose_number3.setMinimumWidth(120)  # Make wider
        for i in range(-64, 65):
            self.transpose_number3.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.transpose_number3.setCurrentIndex(64)  # Default to 0
        keysplit_layout.addWidget(self.transpose_number3, 2, 3)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity:")), 3, 2)
        self.velocity_number3 = QComboBox()
        self.velocity_number3.setMinimumWidth(120)  # Make wider
        for i in range(1, 128):
            self.velocity_number3.addItem(str(i), i)
        self.velocity_number3.setCurrentIndex(126)  # Default to 127
        keysplit_layout.addWidget(self.velocity_number3, 3, 3)
        
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
        
    def send_hid_packet(self, command, data):
        """Send HID packet to device - EXACTLY LIKE WEBAPP"""
        if not self.device or not isinstance(self.device, VialKeyboard):
            raise RuntimeError("Device not connected")
        
        # Create 32-byte packet EXACTLY like webapp
        packet = bytearray(32)
        packet[0] = self.MANUFACTURER_ID  # 0x7D
        packet[1] = self.SUB_ID           # 0x00
        packet[2] = self.DEVICE_ID        # 0x4D
        packet[3] = command
        packet[4] = 0  # Macro num
        packet[5] = 0  # Status
        
        # Copy data payload (max 26 bytes)
        data_len = min(len(data), 26)
        packet[6:6+data_len] = data[:data_len]
        
        try:
            # Send via Vial's via_command method
            self.device.keyboard.via_command(bytes(packet))
        except Exception as e:
            raise RuntimeError(f"Failed to send command: {str(e)}")
    
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
    
    def apply_settings(self, settings):
        """Apply settings dictionary to UI"""
        # Set combo box values by finding matching data
        def set_combo_by_data(combo, value):
            for i in range(combo.count()):
                if combo.itemData(i) == value:
                    combo.setCurrentIndex(i)
                    break
        
        set_combo_by_data(self.velocity_sensitivity, settings.get("velocity_sensitivity", 1))
        set_combo_by_data(self.cc_sensitivity, settings.get("cc_sensitivity", 1))
        set_combo_by_data(self.channel_number, settings.get("channel_number", 0))
        set_combo_by_data(self.transpose_number, settings.get("transpose_number", 0))
        set_combo_by_data(self.transpose_number2, settings.get("transpose_number2", 0))
        set_combo_by_data(self.transpose_number3, settings.get("transpose_number3", 0))
        set_combo_by_data(self.velocity_number, settings.get("velocity_number", 127))
        set_combo_by_data(self.velocity_number2, settings.get("velocity_number2", 127))
        set_combo_by_data(self.velocity_number3, settings.get("velocity_number3", 127))
        set_combo_by_data(self.random_velocity_modifier, settings.get("random_velocity_modifier", 0))
        set_combo_by_data(self.oled_keyboard, settings.get("oled_keyboard", 0))
        set_combo_by_data(self.smart_chord_light, settings.get("smart_chord_light", 0))
        set_combo_by_data(self.smart_chord_light_mode, settings.get("smart_chord_light_mode", 0))
        set_combo_by_data(self.key_split_channel, settings.get("key_split_channel", 0))
        set_combo_by_data(self.key_split2_channel, settings.get("key_split2_channel", 0))
        set_combo_by_data(self.key_split_status, settings.get("key_split_status", 0))
        set_combo_by_data(self.key_split_transpose_status, settings.get("key_split_transpose_status", 0))
        set_combo_by_data(self.key_split_velocity_status, settings.get("key_split_velocity_status", 0))
        set_combo_by_data(self.custom_layer_animations, settings.get("custom_layer_animations_enabled", False))
        set_combo_by_data(self.unsynced_mode, settings.get("unsynced_mode_active", False))
        set_combo_by_data(self.sample_mode, settings.get("sample_mode_active", False))
        set_combo_by_data(self.loop_messaging_enabled, settings.get("loop_messaging_enabled", False))
        set_combo_by_data(self.loop_messaging_channel, settings.get("loop_messaging_channel", 16))
        set_combo_by_data(self.sync_midi_mode, settings.get("sync_midi_mode", False))
        set_combo_by_data(self.alternate_restart_mode, settings.get("alternate_restart_mode", False))
        set_combo_by_data(self.colorblind_mode, settings.get("colorblindmode", 0))
        set_combo_by_data(self.cc_loop_recording, settings.get("cclooprecording", False))
        set_combo_by_data(self.true_sustain, settings.get("truesustain", False))
    
    def pack_basic_data(self, settings):
        """Pack basic settings into 26-byte structure - EXACTLY LIKE WEBAPP"""
        data = bytearray(26)
        
        # Pack 32-bit integers (little endian)
        struct.pack_into('<I', data, 0, settings["velocity_sensitivity"])  # 4 bytes
        struct.pack_into('<I', data, 4, settings["cc_sensitivity"])  # 4 bytes
        
        # Pack single bytes
        offset = 8
        data[offset] = settings["channel_number"]; offset += 1
        data[offset] = settings["transpose_number"] & 0xFF; offset += 1  # Handle signed
        data[offset] = 0; offset += 1  # octave_number (not in UI)
        data[offset] = settings["transpose_number2"] & 0xFF; offset += 1  # Handle signed
        data[offset] = 0; offset += 1  # octave_number2 (not in UI) 
        data[offset] = settings["transpose_number3"] & 0xFF; offset += 1  # Handle signed
        data[offset] = 0; offset += 1  # octave_number3 (not in UI)
        data[offset] = settings["velocity_number"]; offset += 1
        data[offset] = settings["velocity_number2"]; offset += 1
        data[offset] = settings["velocity_number3"]; offset += 1
        data[offset] = settings["random_velocity_modifier"]; offset += 1
        
        # Pack 32-bit integer for oled_keyboard (4 bytes)
        struct.pack_into('<I', data, offset, settings["oled_keyboard"]); offset += 4
        
        # Pack remaining single bytes
        data[offset] = settings["smart_chord_light"]; offset += 1
        data[offset] = settings["smart_chord_light_mode"]; offset += 1
        
        return data
    
    def pack_advanced_data(self, settings):
        """Pack advanced settings into 15-byte structure - EXACTLY LIKE WEBAPP"""
        data = bytearray(15)
        
        offset = 0
        data[offset] = settings["key_split_channel"]; offset += 1
        data[offset] = settings["key_split2_channel"]; offset += 1
        data[offset] = settings["key_split_status"]; offset += 1
        data[offset] = settings["key_split_transpose_status"]; offset += 1
        data[offset] = settings["key_split_velocity_status"]; offset += 1
        data[offset] = 1 if settings["custom_layer_animations_enabled"] else 0; offset += 1
        data[offset] = 1 if settings["unsynced_mode_active"] else 0; offset += 1
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
            settings = self.get_current_settings()
            
            # Pack and send basic data with slot number
            basic_data = self.pack_basic_data(settings)
            data_with_slot = bytearray([slot]) + basic_data
            self.send_hid_packet(self.HID_CMD_SAVE_KEYBOARD_SLOT, data_with_slot)
            
            # Small delay then send advanced data
            QtCore.QTimer.singleShot(50, lambda: self._send_advanced_data(settings))
            
            slot_name = "default settings" if slot == 0 else f"Slot {slot}"
            QMessageBox.information(None, "Success", f"Settings saved as {slot_name}")
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save to slot {slot}: {str(e)}")
    
    def _send_advanced_data(self, settings):
        """Send advanced data (helper for save operations)"""
        try:
            advanced_data = self.pack_advanced_data(settings)
            self.send_hid_packet(self.HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED, advanced_data)
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to send advanced data: {str(e)}")
    
    def on_load_slot(self, slot):
        """Load settings from slot"""
        try:
            self.send_hid_packet(self.HID_CMD_LOAD_KEYBOARD_SLOT, [slot])
            slot_name = "default settings" if slot == 0 else f"Slot {slot}"
            QMessageBox.information(None, "Info", f"Load request sent for {slot_name}")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to load from slot {slot}: {str(e)}")
    
    def on_reset(self):
        """Reset to default settings"""
        try:
            reply = QMessageBox.question(None, "Confirm Reset", 
                                       "Reset all keyboard settings to defaults? This cannot be undone.",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.send_hid_packet(self.HID_CMD_RESET_KEYBOARD_CONFIG, [])
                # Also reset UI to defaults
                self.reset_ui_to_defaults()
                QMessageBox.information(None, "Success", "Settings reset to defaults")
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
            "unsynced_mode_active": False,
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